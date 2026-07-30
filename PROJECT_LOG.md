# Financial NER LLM — Project Log

Fine-tuning an open-weight LLM to extract structured financial entities from
SEC filing text, with a full MLOps pipeline around it: SageMaker training,
CI/CD-gated evaluation, model registry, and (planned) production deployment
and monitoring. This doc tracks what's been built, why, and what's left.

---

## 1. Why this project exists

Built specifically to close a cluster of MLOps/AI-engineering gaps that kept
showing up across job descriptions but weren't backed by any existing
project: LLM fine-tuning (LoRA/QLoRA), a cloud-managed ML platform
(SageMaker), CI/CD for AI services, model monitoring, observability, A/B
testing, and financial-services domain experience. Rather than treat these
as separate side quests, one coherent pipeline was designed to hit all of
them: fine-tune → SageMaker Pipeline → CI/CD gate → registry → deploy →
monitor.

Deliberately **not** chasing gaps for their own sake. Considered and
rejected along the way: MLflow (redundant with SageMaker's native Model
Registry), Triton/TensorRT (no JD ever asked for it), a full document-
ingestion frontend/backend (real, but scoped as v3, after the core pipeline
ships), PII detection as the primary task (financial entity extraction was
judged the stronger, more differentiated choice).

---

## 2. The task

**Financial entity extraction**: given a sentence from a financial filing,
extract entities into 5 coarse types — `MONETARY_AMOUNT`, `PERCENTAGE`,
`NUMBER`, `DATE`, `DURATION` — as a compact JSON list, e.g.

```json
[{"type": "monetary_amount", "text": "$50.0 million"}, {"type": "percentage", "text": "4.25%"}]
```

Framed as **generative structured extraction** (a decoder LLM generating
JSON), not classic BIO token classification, specifically because the goal
was to demonstrate genuine decoder-LLM fine-tuning, not just an encoder
classifier head.

**Base model**: Qwen2.5-7B-Instruct (chosen over Llama 3.1 8B for: no
license-gating friction, strong native structured-output/JSON tendency, and
confirmed support in TRL's patched-chat-template list needed for
`assistant_only_loss`).

**Fine-tuning method**: QLoRA — 4-bit NF4 quantization with double
quantization, `bnb_4bit_compute_dtype=bfloat16`, LoRA rank 16 / alpha 32 /
dropout 0.05, targeting `all-linear`. `paged_adamw_8bit` optimizer,
`sdpa` attention (flash-attn kernel routes were tried and abandoned after
repeated environment friction — see §6).

---

## 3. Data pipeline

**Source**: FiNER-139 (SEC filings, ~900K training sentences, 139 XBRL
concept tags in BIO format).

**Label collapsing (139 → 5)**: Rather than train on 139 mostly-rare XBRL
concepts, each concept was mapped to one of the 5 coarse types via
keyword-based rules, refined through several rounds of manual auditing
against the real concept list:
- Caught and fixed: `LongTermDebt`/`ShortTermDebt` false-matching a bare
  `"Term"` keyword into `duration` instead of `monetary_amount`.
- Caught and fixed: `...InPeriod`/`...DuringPeriod`/`...AtPeriodEnd`
  qualifiers false-matching into `duration` when the actual value was a
  count, amount, or rate (XBRL uses "period" as a timing qualifier far more
  often than as the actual value type).
- Caught and fixed: `...GrantDateFairValue`-style concepts false-matching
  `date` when the real value was a fair-value amount (fixed by anchoring
  the date rule to end-of-string).
- Caught and fixed: bare `Number` suffix (e.g. `...ClaimsNumber`) not
  matching the `NumberOf`-only keyword.
- 4 concepts required manual override entries where no keyword rule could
  resolve them correctly.
- `area` (1 concept) folded into `number` — too rare to justify its own
  class.

**BIO → generative JSON conversion**: groups consecutive B-/I- tokens into
spans, reconstructs readable text (lightweight detokenization to avoid
`" comma ,"`-style artifacts), builds `{system, user, assistant}` chat-
formatted examples. Validated with a substring-match pass (every extracted
entity's text must appear in its source sentence) before pushing to the Hub.

**Class imbalance handling**: training subset built via stratified sampling
(all rare-type examples + capped samples of common/no-entity examples)
rather than random sampling, specifically to avoid starving `date`/
`duration` of training signal given `monetary_amount` dominates the raw
concept distribution ~59% to ~2%.

**Dataset published**: `AG2307/financial-ner-llm-data` on the Hub
(messages-format, train/validation splits).

---

## 4. Training

Built on `trl`'s `SFTTrainer` (chosen over a hand-rolled PyTorch loop
specifically because the one genuinely risky piece, prompt-completion
masking, is exactly what the library gets right and a custom loop would be
most likely to silently get wrong). Key config decisions and why:

- `assistant_only_loss=True` — masks loss to the assistant turn only, using
  TRL's patched chat-template generation markers (Qwen supported natively).
- Compact single-line JSON completions (not pretty-printed) — fewer
  tokens, simpler for the model to learn, easier to parse at eval time.
- `warmup_steps` computed manually (not `warmup_ratio`, deprecated in the
  installed transformers version), `lr_scheduler_type="cosine"`,
  `weight_decay=0.01`.
- `max_length` (SFTConfig's training-time sequence cap) raised from 512 to
  2048 after discovering ~1.5%+ of examples were being silently truncated
  mid-completion at 512 tokens — meaning the model never saw complete
  target JSON for entity-dense examples. This was a real bug, not just a
  tuning knob.
- Custom `EntityF1Callback` (`on_evaluate` hook): runs real batched
  generation (not teacher-forced) against a held-out sample, computes
  precision/recall/F1 (micro, macro, per-type), logs to W&B and merges into
  the trainer's `log_history`. Built specifically because teacher-forced
  metrics (`eval_loss`, `mean_token_accuracy`) are misleading proxies —
  proven concretely when the baseline showed 79% token accuracy but 0.0
  entity-F1 pre-fine-tuning, since teacher-forced accuracy mostly rewards
  copying visible context and predictable JSON syntax, not genuine
  extraction.

**Environment debugging** (molab, a rented GPU notebook environment): a
long chain of issues, most non-obvious — `torch`/`torchvision` version
mismatch from a leaked system `site-packages` path polluting the venv;
`peft` genuinely missing after a config change; `IPython` missing (needed
transitively by `transformers.Trainer`'s notebook progress bar); a
`kernels-community/flash-attn2` Hub-kernel reference failing because the
`kernels` package wasn't installed, ultimately abandoned in favor of
`sdpa` given repeated friction; a QLoRA "cannot fine-tune purely quantized
model" error fixed by explicit `prepare_model_for_kbit_training` +
`get_peft_model` instead of relying on `SFTTrainer`'s automatic PEFT
wrapping.

---

## 5. Evaluation methodology (the deepest, most valuable investigation)

**Core finding: raw precision on FiNER's gold labels understates true
model quality**, and this was established with real evidence, not assumed.

- **Tokenizer-source bug**: an early standalone eval run loaded the
  tokenizer from the raw base model repo instead of the fine-tuned
  adapter's repo, missing TRL's patched chat template. Symptom: the model
  invented label categories it was never trained on (`RATING`,
  `InterestRate`, `Capital Stock`...) — a classic signature of prompt-
  format mismatch, not a bad model. Fixed by loading the tokenizer from the
  adapter repo (where `processing_class=tokenizer` had it saved during
  training).
- **Gold-label sparsity (XBRL selective tagging)**: manual inspection of a
  dense debt-schedule example showed ~18 untagged dollar figures against 4
  tagged ones — XBRL only tags facts mapped to specific required taxonomy
  concepts, not every number in a table. Confirmed again with narrative
  magnitude mentions ("5 billion", "450 million") that are almost never
  XBRL-tagged since they live in prose, not structured statements.
  Confirmed a third time, most starkly, on `DATE`: only 8 genuinely
  gold-tagged dates in a 10,000-example sweep, while the model correctly
  finds real dates far more often — precision for that one class collapses
  almost entirely from arithmetic, not model error, when nearly every
  correct extraction has nowhere to land as a true positive.
- **Explicit decision made not to "fix" this by suppressing correct
  extractions** (e.g. via prompt engineering to match gold's narrow scope)
  — that would optimize the metric at the expense of the actual model
  being worse. Documented as a known eval-methodology limitation instead.
- **Small-sample eval bias**: the in-training `EntityF1Callback` (600
  samples, drawn from the rare-class-stratified `eval_subset`) reported
  much higher macro-F1 than a full, natural-distribution sweep. Root
  cause diagnosed precisely: `DATE`'s catastrophic real-world precision
  was almost invisible in a small, stratified sample specifically because
  the stratification was built to protect *recall* on rare classes during
  *training*, not to be representative for *eval*.

**Where this leaves the model**: strong recall throughout (~0.93-0.94)
across every version of the eval; every manually-inspected gold/pred pair
with real gold content matches exactly; raw precision (~0.62-0.66) is
believed to meaningfully understate true quality but this hasn't yet been
converted into a fully quantified adjusted number (a manual false-positive
adjudication pass on a random sample would do that — noted as optional
polish, not blocking).

---

## 6. MLOps infrastructure

**SageMaker Pipeline**: `TrainingStep → evaluation step → ConditionStep
(F1 threshold) → RegisterModel`. Registered models default to
`PendingManualApproval` — automated gate decides whether a model is even
*eligible*, a human still signs off before anything is deployed. Chosen
over a hand-rolled blocking script specifically because it doesn't require
a CI runner to block for hours, and it's the AWS-native tool built for
exactly this DAG.

**CI/CD** (`.github/workflows/ci.yml`): `uv`-based lint (`ruff check` +
`ruff format --check`) and a `py_compile` smoke test on push/PR; a
separate `trigger-pipeline` job (push-to-main only, explicitly excluded
from `pull_request` events to avoid accidentally billing a PR) that
authenticates to AWS and calls `sm_trigger.py` to start the Pipeline.
`workflow_dispatch` kept alongside push-triggering for manual testing.

**AWS authentication — workload identity federation (OIDC), not stored
access keys**: chosen deliberately as the more production-correct pattern
over a simpler IAM-user-with-access-key approach, since it avoids any
long-lived credential sitting in GitHub's secret store. Two distinct IAM
roles, doing two distinct jobs:
- `GitHubActions-Trigger-Financial-NER-LLM` — assumed via OIDC (trust
  policy scoped to `repo:AG2307/financial-ner-llm:ref:refs/heads/main`
  specifically, not a wildcard). Permissions: `AmazonSageMakerFullAccess`,
  plus a scoped inline policy for `iam:PassRole` (on the execution role
  specifically) and S3 access (for the SDK's `source_dir` packaging
  upload, which happens under the *caller's* credentials before any
  training job exists).
- `SageMakerExecutionRole-Financial-NER-LLM` — what the training job
  itself runs as once started. Separate, explicit S3 policy added rather
  than relying on `AmazonSageMakerFullAccess`'s partial (bucket-name-
  pattern-scoped) S3 coverage.

**Secrets**: `HF_TOKEN`/`WANDB_API_KEY` handled via `.env` +
`python-dotenv` locally (Studio/molab), and GitHub Actions repo Secrets in
CI — never touch the training container's code path directly, since
SageMaker injects the Estimator's `environment={}` dict as real env vars
inside the container.

---

## 7. Current status

- [x] Data pipeline built, validated, published to the Hub
- [x] Training script working (QLoRA + SFTTrainer + EntityF1Callback)
- [x] Multiple training runs completed in molab (96GB card), F1 up to
      ~0.90 micro / ~0.89 macro on a small stratified sample after 2 epochs
- [x] Full-eval-set methodology investigation completed (see §5)
- [x] SageMaker Pipeline built: train → eval → ConditionStep → register
- [x] CI/CD wired up end to end with OIDC — **confirmed working**,
      manually triggered via `workflow_dispatch`
- [ ] Batch size / gradient accumulation not yet recalibrated for the
      actual (smaller than 96GB) SageMaker training instance
- [ ] A full pipeline run on real SageMaker infrastructure, training
      through the ConditionStep gate to a registered model, not yet
      completed
- [ ] Endpoint deployment not started
- [ ] Model approval step not yet exercised for a real candidate

---

## 8. Roadmap

**v1 (current focus)** — finish what's above: recalibrate batch size for
the real instance, get a full Pipeline run through to a registered,
approved model, deploy it behind a SageMaker real-time endpoint. Decision
made to use AWS's pre-built LMI container with the vLLM backend for this,
*not* a custom (BYOC) container — the metrics-access advantage of BYOC
only matters once Prometheus is actually in the picture, which is v2, not
v1. Closes the DevOps/MLOps-facing gaps this whole project was built
around.

**v2 (DevOps-focused)** — EKS deployment and Prometheus/Grafana
monitoring. Revisit BYOC vs LMI at that point, since EKS has no
`/ping`+`/invocations`-only restriction the way SageMaker does, so a BYOC
container running vLLM's own standalone server (with its native
`/metrics` endpoint) becomes the natural choice there, no Pushgateway
workaround needed the way it would be on SageMaker. Also the natural home
for closing the standing Kubernetes/container-orchestration gap
(every project up to now stops at Docker Compose).

**v3 (application-facing, "AI engineering" side)** — full frontend +
backend + database on top, document ingestion (PDF/OCR), async processing
with a real webhook notification on completion (closes the standing
Webhooks gap), ties this project even more directly to Docusign-style
document-workflow relevance.

---

## 9. Honest limitations (for whenever this gets written up properly)

- Precision numbers on FiNER's natural validation distribution are lower
  than the model's true practical quality, for reasons explained in §5 —
  state this explicitly rather than letting a bare number stand alone.
- No entity offset/position tracking — the generative-extraction framing
  gives `(type, text)` pairs, not character offsets. Recoverable via
  post-hoc string search if ever needed (e.g. for a document-highlighting
  UI in v3), but not built.
- `DATE` is a genuinely hard class to get a clean precision read on given
  how sparse gold tagging is for it — worth being upfront about this
  rather than implying uniform performance across all 5 types.
- Extreme entity-dense examples (50+ entities in one sentence) are a real
  edge case; `max_length=2048` covers the large majority but not the most
  extreme outliers observed (up to ~2148 tokens).
