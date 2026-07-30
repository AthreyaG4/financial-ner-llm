import argparse
import json
import os
import time

import torch
import wandb
from datasets import concatenate_datasets, load_dataset
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from tqdm.auto import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainerCallback,
)
from trl import SFTConfig, SFTTrainer

hf_token = os.environ["HF_TOKEN"]


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "1"):
        return True
    if v.lower() in ("no", "false", "f", "0"):
        return False
    raise argparse.ArgumentTypeError(f"Boolean value expected, got {v!r}")


def parse_args():
    parser = argparse.ArgumentParser()

    # model / data
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument(
        "--dataset_id", type=str, default="AG2307/financial-ner-llm-data"
    )

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--wandb_run_name", type=str, default=None)

    # dataset subset sizes (class-balance sampling)
    parser.add_argument("--train_common_size", type=int, default=15000)
    parser.add_argument("--train_none_size", type=int, default=5000)
    parser.add_argument("--eval_common_size", type=int, default=1500)
    parser.add_argument("--eval_none_size", type=int, default=500)

    # LoRA
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--lora_target_modules", type=str, default="all-linear")

    # training
    parser.add_argument("--num_train_epochs", type=int, default=4)
    parser.add_argument("--per_device_train_batch_size", type=int, default=16)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=16)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--warmup_ratio", type=float, default=0.03)
    parser.add_argument("--lr_scheduler_type", type=str, default="cosine")
    parser.add_argument("--max_length", type=int, default=2048)
    parser.add_argument("--optim", type=str, default="paged_adamw_8bit")
    parser.add_argument("--logging_steps", type=int, default=10)
    parser.add_argument("--assistant_only_loss", type=str2bool, default=True)
    parser.add_argument("--gradient_checkpointing", type=str2bool, default=False)
    parser.add_argument("--bf16", type=str2bool, default=True)

    # entity-F1 eval callback
    parser.add_argument("--eval_f1_num_samples", type=int, default=600)
    parser.add_argument("--eval_max_new_tokens", type=int, default=2048)

    # export / hub
    parser.add_argument("--merge_weights", type=str2bool, default=False)
    parser.add_argument("--push_to_hub", type=str2bool, default=True)
    parser.add_argument(
        "--hub_model_id", type=str, default="AG2307/financial-ner-llm-qwen2.5-7b-qlora"
    )

    return parser.parse_args()


args = parse_args()

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

peft_config = LoraConfig(
    r=args.lora_r,
    lora_alpha=args.lora_alpha,
    lora_dropout=args.lora_dropout,
    target_modules=args.lora_target_modules,
    task_type="CAUSAL_LM",
)

wandb_run_name = args.wandb_run_name or (
    f"{args.model_id.split('/')[-1].lower()}-qlora-{time.strftime('%Y%m%d-%H%M%S')}"
)
wandb.init(project="financial-ner-llm", name=wandb_run_name)

model_id = args.model_id

tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    attn_implementation="sdpa",
    dtype=torch.bfloat16,
    token=hf_token,
)
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

dataset = load_dataset(args.dataset_id, token=hf_token)


def has_rare_type(example):
    entities = json.loads(example["messages"][2]["content"])
    return any(e["type"] in {"DATE", "DURATION"} for e in entities)


def has_entities_no_rare(example):
    entities = json.loads(example["messages"][2]["content"])
    return len(entities) > 0 and not any(
        e["type"] in {"DATE", "DURATION"} for e in entities
    )


def has_no_entities(example):
    return json.loads(example["messages"][2]["content"]) == []


train = dataset["train"]
train_rare = train.filter(has_rare_type, num_proc=4)
train_common = (
    train.filter(has_entities_no_rare, num_proc=4)
    .shuffle(seed=args.seed)
    .select(range(args.train_common_size))
)
train_none = (
    train.filter(has_no_entities, num_proc=4)
    .shuffle(seed=args.seed)
    .select(range(args.train_none_size))
)

val = dataset["validation"]
eval_rare = val.filter(has_rare_type, num_proc=4)
eval_common = (
    val.filter(has_entities_no_rare, num_proc=4)
    .shuffle(seed=args.seed)
    .select(range(min(args.eval_common_size, len(val))))
)
eval_none = (
    val.filter(has_no_entities, num_proc=4)
    .shuffle(seed=args.seed)
    .select(range(min(args.eval_none_size, len(val))))
)

train_subset = concatenate_datasets([train_rare, train_common, train_none]).shuffle(
    seed=args.seed
)

eval_subset = concatenate_datasets([eval_rare, eval_common, eval_none]).shuffle(
    seed=args.seed
)


class EntityF1Callback(TrainerCallback):
    def __init__(
        self,
        model,
        tokenizer,
        eval_examples,
        num_samples=600,
        batch_size=16,
        max_new_tokens=2048,
        seed=42,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.eval_examples = eval_examples.shuffle(seed=seed).select(
            range(min(num_samples, len(eval_examples)))
        )
        self.batch_size = batch_size
        self.max_new_tokens = max_new_tokens

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        self.model.eval()
        original_padding_side = self.tokenizer.padding_side
        self.tokenizer.padding_side = "left"

        tp = fp = fn = 0
        per_type = {}

        for i in tqdm(
            range(0, len(self.eval_examples), self.batch_size),
            desc="Entity F1 eval",
            leave=False,
        ):
            batch = self.eval_examples[i : i + self.batch_size]
            prompts = [
                self.tokenizer.apply_chat_template(
                    msgs[:2],
                    tokenize=False,
                    add_generation_prompt=True,
                    max_tokens=2048,
                )
                for msgs in batch["messages"]
            ]
            gold = [json.loads(msgs[2]["content"]) for msgs in batch["messages"]]

            inputs = self.tokenizer(prompts, return_tensors="pt", padding=True).to(
                self.model.device
            )
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                )

            generated = output_ids[
                :, inputs["input_ids"].shape[1] :
            ]  # strip the prompt back off
            decoded = self.tokenizer.batch_decode(generated, skip_special_tokens=True)

            for pred_text, gold_entities in zip(decoded, gold):
                try:
                    pred_entities = json.loads(pred_text)
                    if not isinstance(pred_entities, list):
                        pred_entities = []
                    else:
                        pred_entities = [
                            e
                            for e in pred_entities
                            if isinstance(e, dict) and "type" in e and "text" in e
                        ]
                except json.JSONDecodeError:
                    pred_entities = []

                pred_set = {(e["type"], e["text"]) for e in pred_entities}
                gold_set = {(e["type"], e["text"]) for e in gold_entities}

                tp += len(pred_set & gold_set)
                fp += len(pred_set - gold_set)
                fn += len(gold_set - pred_set)

                for etype in {t for t, _ in pred_set} | {t for t, _ in gold_set}:
                    per_type.setdefault(etype, [0, 0, 0])
                    p_set = {t for t in pred_set if t[0] == etype}
                    g_set = {t for t in gold_set if t[0] == etype}
                    per_type[etype][0] += len(p_set & g_set)
                    per_type[etype][1] += len(p_set - g_set)
                    per_type[etype][2] += len(g_set - p_set)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1_micro = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        per_type_f1 = {}
        for etype, (t, f_p, f_n) in per_type.items():
            p = t / (t + f_p) if (t + f_p) else 0.0
            r = t / (t + f_n) if (t + f_n) else 0.0
            per_type_f1[etype] = 2 * p * r / (p + r) if (p + r) else 0.0
        f1_macro = sum(per_type_f1.values()) / len(per_type_f1) if per_type_f1 else 0.0

        results = {
            "eval_entity_precision": precision,
            "eval_entity_recall": recall,
            "eval_entity_f1_micro": f1_micro,
            "eval_entity_f1_macro": f1_macro,
        }
        results.update({f"eval_entity_f1_{t}": f for t, f in per_type_f1.items()})

        if metrics is not None:
            metrics.update(results)

        print(
            f"[Epoch {state.epoch:.0f}] entity F1 micro={f1_micro:.4f} macro={f1_macro:.4f} "
            f"precision={precision:.4f} recall={recall:.4f}"
        )
        wandb.log(results)

        self.tokenizer.padding_side = original_padding_side
        self.model.train()


num_examples = len(train_subset)
effective_batch_size = (
    args.per_device_train_batch_size * args.gradient_accumulation_steps
)
total_steps = (num_examples // effective_batch_size) * args.num_train_epochs
warmup_steps = int(total_steps * args.warmup_ratio)

config = SFTConfig(
    output_dir="/opt/ml/checkpoints",
    per_device_train_batch_size=args.per_device_train_batch_size,
    per_device_eval_batch_size=args.per_device_eval_batch_size,
    gradient_accumulation_steps=args.gradient_accumulation_steps,
    num_train_epochs=args.num_train_epochs,
    learning_rate=args.learning_rate,
    weight_decay=args.weight_decay,
    assistant_only_loss=args.assistant_only_loss,
    save_strategy="epoch",
    eval_strategy="epoch",
    eval_on_start=True,
    logging_first_step=True,
    warmup_steps=warmup_steps,
    lr_scheduler_type=args.lr_scheduler_type,
    logging_strategy="steps",
    logging_steps=args.logging_steps,
    report_to="wandb",
    gradient_checkpointing=args.gradient_checkpointing,
    bf16=args.bf16,
    optim=args.optim,
    max_length=args.max_length,
    push_to_hub=args.push_to_hub,
    hub_model_id=args.hub_model_id,
    hub_token=hf_token,
    resume_from_checkpoint=True,
    seed=args.seed,
)

trainer = SFTTrainer(
    model=model,
    args=config,
    train_dataset=train_subset,
    eval_dataset=eval_subset,
    processing_class=tokenizer,
)

trainer.add_callback(
    EntityF1Callback(
        model,
        tokenizer,
        eval_subset,
        num_samples=args.eval_f1_num_samples,
        batch_size=args.per_device_eval_batch_size,
        max_new_tokens=args.eval_max_new_tokens,
        seed=args.seed,
    )
)

trainer.train()

if args.merge_weights:
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(os.environ["SM_MODEL_DIR"])
    tokenizer.save_pretrained(os.environ["SM_MODEL_DIR"])
else:
    trainer.save_model(os.environ["SM_MODEL_DIR"])

trainer.add_callback(
    EntityF1Callback(
        model,
        tokenizer,
        eval_subset,
        num_samples=600,
        batch_size=8,
        max_new_tokens=2048,
    )
)

trainer.train()
trainer.save_model(os.environ["SM_MODEL_DIR"])
