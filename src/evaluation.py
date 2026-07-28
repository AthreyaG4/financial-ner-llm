from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from peft import PeftModel
from datasets import load_dataset
import torch
import os
import json
from tqdm.auto import tqdm

hf_token = os.getenv("HF_TOKEN")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

tokenizer = AutoTokenizer.from_pretrained(
    "AG2307/financial-ner-llm-qwen2.5-7b-qlora", token=hf_token
)

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    quantization_config=bnb_config,
    device_map="auto",
    attn_implementation="sdpa",
    token=hf_token,
)
model = PeftModel.from_pretrained(
    model, model_id="AG2307/financial-ner-llm-qwen2.5-7b-qlora"
)
model.eval()

data = load_dataset("AG2307/financial-ner-llm-data", token=hf_token)
val_data = data["validation"].select(range(10000))

tokenizer.padding_side = "left"


def compute_entity_f1(model, val_data, batch_size=16, max_new_tokens=2048):
    tp = fp = fn = 0
    per_type = {}
    examples = []

    for i in tqdm(range(0, len(val_data), batch_size), desc="Generating", leave=False):
        batch = val_data[i : i + batch_size]

        prompts = [
            tokenizer.apply_chat_template(
                msgs[:2], tokenize=False, add_generation_prompt=True
            )
            for msgs in batch["messages"]
        ]
        gold = [json.loads(msgs[2]["content"]) for msgs in batch["messages"]]

        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=2048,
        ).to(model.device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs, max_new_tokens=max_new_tokens, do_sample=False
            )

        generated = output_ids[:, inputs["input_ids"].shape[1] :]
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)

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

            examples.append(
                {
                    "gold": gold_entities,
                    "predicted": pred_entities,
                    "raw_output": pred_text,
                }
            )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1_micro = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )

    per_type_f1 = {}
    for etype, (t, f_p, f_n) in per_type.items():
        p = t / (t + f_p) if (t + f_p) else 0.0
        r = t / (t + f_n) if (t + f_n) else 0.0
        per_type_f1[etype] = 2 * p * r / (p + r) if (p + r) else 0.0
    f1_macro = sum(per_type_f1.values()) / len(per_type_f1) if per_type_f1 else 0.0

    metrics = {
        "precision": precision,
        "recall": recall,
        "f1_micro": f1_micro,
        "f1_macro": f1_macro,
        **{f"f1_{t}": f for t, f in per_type_f1.items()},
    }
    return metrics, examples


metrics, examples = compute_entity_f1(model, val_data, batch_size=16)
evaluation_output_path = os.path.join(
    "/opt/ml/processing/evaluation", "evaluation.json"
)
with open(evaluation_output_path, "w") as f:
    f.write(json.dumps(metrics))
