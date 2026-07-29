import os
import time

from dotenv import load_dotenv
from sagemaker.core.helper.session_helper import Session
from sagemaker.core.model_metrics import MetricsSource, ModelMetrics
from sagemaker.core.processing import FrameworkProcessor
from sagemaker.core.shapes.shapes import ProcessingOutput, ProcessingS3Output
from sagemaker.core.workflow import ConditionGreaterThanOrEqualTo
from sagemaker.core.workflow.functions import Join, JsonGet
from sagemaker.core.workflow.parameters import (
    ParameterInteger,
    ParameterString,
)
from sagemaker.core.workflow.pipeline_context import PipelineSession
from sagemaker.core.workflow.properties import PropertyFile
from sagemaker.mlops.workflow.condition_step import ConditionStep
from sagemaker.mlops.workflow.model_step import ModelStep
from sagemaker.mlops.workflow.pipeline import Pipeline
from sagemaker.mlops.workflow.steps import CacheConfig, ProcessingStep, TrainingStep
from sagemaker.serve.model_builder import ModelBuilder
from sagemaker.train.configs import (
    CheckpointConfig,
    Compute,
    OutputDataConfig,
    SourceCode,
    StoppingCondition,
)
from sagemaker.train.model_trainer import ModelTrainer

load_dotenv()

# Create a SageMaker session
session = Session()
pipeline_session = PipelineSession()
role = "arn:aws:iam::186189159492:role/SageMakerExecutionRole-Financial-NER-LLM"
cache_config = CacheConfig(enable_caching=True, expire_after="30d")

training_instance_type = ParameterString(
    name="TrainingInstanceType", default_value="ml.g5.2xlarge"
)
training_instance_count = ParameterInteger(name="InstanceCount", default_value=1)
evaluation_instance_type = ParameterString(
    name="EvaluationInstanceType", default_value="ml.g5.2xlarge"
)
evaluation_instance_count = ParameterInteger(
    name="EvaluationInstanceCount", default_value=1
)
model_approval_status = ParameterString(
    name="ModelApprovalStatus", default_value="PendingManualApproval"
)
model_package_group_name = ParameterString(
    name="ModelPackageGroupName",
    default_value="FinancialNERLLMModelPackageGroup",
)

image_uri = "763104351884.dkr.ecr.eu-west-1.amazonaws.com/pytorch:2.13.0-cu133-amzn2023-sagemaker"

print(f"Using role: {role}")
print(f"Default bucket: {session.default_bucket()}")
print(f"Region: {session.boto_region_name}")

train_job_name = (
    f"qwen-2-5-7b-qlora-train-{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
)
model_id = "Qwen/Qwen2.5-7B-Instruct"

hyperparameters = {
    "model_id": model_id,
    "dataset_id": "AG2307/financial-ner-llm-data",
    "seed": 42,
    # LoRA
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "lora_target_modules": "all-linear",
    # dataset subset sizes (class-balance sampling)
    "train_common_size": 15000,
    "train_none_size": 5000,
    "eval_common_size": 1500,
    "eval_none_size": 500,
    # training
    "num_train_epochs": 3,
    "per_device_train_batch_size": 16,
    "per_device_eval_batch_size": 16,
    "gradient_accumulation_steps": 2,
    "learning_rate": 1e-4,
    "weight_decay": 0.01,
    "warmup_ratio": 0.03,
    "lr_scheduler_type": "cosine",
    "max_length": 2048,
    "optim": "paged_adamw_8bit",
    "logging_steps": 10,
    "assistant_only_loss": True,
    "gradient_checkpointing": True,
    "bf16": True,
    # entity-F1 eval callback
    "eval_f1_num_samples": 600,
    "eval_max_new_tokens": 2048,
    # export / hub
    "merge_weights": False,
    "push_to_hub": True,
    "hub_model_id": "AG2307/financial-ner-llm-qwen2.5-7b-qlora",
}

trainer = ModelTrainer(
    training_image="763104351884.dkr.ecr.eu-west-1.amazonaws.com/pytorch:2.13.0-cu133-amzn2023-sagemaker",
    source_code=SourceCode(
        source_dir="./src",
        entry_script="train.py",
        requirements="requirements.txt",
    ),
    role=role,
    base_job_name=train_job_name,
    compute=Compute(
        instance_type=training_instance_type,
        instance_count=training_instance_count,
        volume_size_in_gb=300,
    ),
    stopping_condition=StoppingCondition(max_runtime_in_seconds=36000),
    sagemaker_session=pipeline_session,
    output_data_config=OutputDataConfig(
        s3_output_path=f"s3://{session.default_bucket()}/{train_job_name}/output",
        compression_type="GZIP",
    ),
    checkpoint_config=CheckpointConfig(
        s3_uri=f"s3://{session.default_bucket()}/{train_job_name}/checkpoints",
        local_path="/opt/ml/checkpoints",
    ),
    hyperparameters=hyperparameters,
    environment={
        "HF_TOKEN": os.environ.get("HF_TOKEN"),
        "WANDB_API_KEY": os.environ.get("WANDB_API_KEY"),
    },
)

train_args = trainer.train()

step_train = TrainingStep(
    name="TrainModelStep",
    step_args=train_args,
    cache_config=cache_config,
)

eval_job_name = (
    f"qwen-2-5-7b-qlora-eval-{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
)

eval_processor = FrameworkProcessor(
    image_uri="763104351884.dkr.ecr.eu-west-1.amazonaws.com/pytorch:2.13.0-cu133-amzn2023-sagemaker",
    instance_type=evaluation_instance_type,
    instance_count=evaluation_instance_count,
    base_job_name=eval_job_name,
    sagemaker_session=pipeline_session,
    role=role,
    env={
        "HF_TOKEN": os.environ.get("HF_TOKEN"),
    },
)

eval_processor_args = eval_processor.run(
    code="evaluation.py",
    source_dir="src",
    requirements="requirements.txt",
    outputs=[
        ProcessingOutput(
            output_name="evaluation",
            s3_output=ProcessingS3Output(
                s3_uri=f"s3://{session.default_bucket()}/{eval_job_name}/evaluation",
                local_path="/opt/ml/processing/evaluation",
                s3_upload_mode="EndOfJob",
            ),
        )
    ],
)

evaluation_report = PropertyFile(
    name="EvaluationReport", output_name="evaluation", path="evaluation.json"
)

step_eval = ProcessingStep(
    name="EvaluationStep",
    step_args=eval_processor_args,
    property_files=[evaluation_report],
)

model_metrics = ModelMetrics(
    model_statistics=MetricsSource(
        s3_uri=Join(
            on="/",
            values=[
                step_eval.properties.ProcessingOutputConfig.Outputs[
                    "evaluation"
                ].S3Output.S3Uri,
                "evaluation.json",
            ],
        ),
        content_type="application/json",
    )
)

model_builder = ModelBuilder(
    s3_model_data_url=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    image_uri="763104351884.dkr.ecr.eu-west-1.amazonaws.com/pytorch:2.13.0-cu133-amzn2023-sagemaker",
    sagemaker_session=pipeline_session,
    role_arn=role,
)

step_create_model = ModelStep(
    name="CreateModel",
    step_args=model_builder.build(),
)

step_register_model = ModelStep(
    name="RegisterModel",
    step_args=model_builder.register(
        model_package_group_name=model_package_group_name,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.t2.medium", "ml.m5.xlarge"],
        transform_instances=["ml.m5.xlarge"],
        approval_status=model_approval_status,
        model_metrics=model_metrics,
    ),
)

cond_gte = ConditionGreaterThanOrEqualTo(
    left=JsonGet(
        step_name=step_eval.name,
        property_file=evaluation_report,
        json_path="metrics.entity_f1.value",
    ),
    right=0.8,
)

step_cond = ConditionStep(
    name="FinancialNERLLMF1Condition",
    conditions=[cond_gte],
    if_steps=[step_create_model, step_register_model],
    else_steps=[],
)

pipeline = Pipeline(
    name="FinancialNERLLMPipeline",
    parameters=[
        training_instance_type,
        evaluation_instance_type,
        training_instance_count,
        evaluation_instance_count,
        model_approval_status,
        model_package_group_name,
    ],
    steps=[step_train, step_eval, step_cond],
    sagemaker_session=pipeline_session,
)

pipeline.definition()
pipeline.upsert(role_arn=role)
execution = pipeline.start()
