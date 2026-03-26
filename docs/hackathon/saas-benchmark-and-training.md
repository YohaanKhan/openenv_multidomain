# SaaS Benchmark and Training

## Why SaaS is the training target

The SaaS domain is the clearest demonstration domain for small-model evaluation
and fine-tuning because it combines:

- realistic business workflows
- deterministic expert solutions
- structured tool actions
- meaningful reward shaping
- strong grader feedback

It is complex enough to expose failure modes, but constrained enough to support
clean expert demonstration generation.

## Local benchmark workflow

The local benchmark path uses Ollama rather than the OpenAI submission baseline.
This lets us:

- test smaller models locally
- compare before/after training
- save repeated-run benchmark evidence

The benchmark runner records:

- task-level scores
- mean average score
- success rate
- average turns
- invalid action rate

Repeated runs are written under `benchmark_results/` and aggregate summaries can
be compared later.

## Current baseline snapshot

The first stable repeated-run baseline for the upgraded SaaS domain used
`qwen2.5:1.5b` over 10 full benchmark runs. Each run covered `saas_easy`,
`saas_medium`, and `saas_hard` under the same tools, prompts, rewards, and
graders.

| Model | Runs | saas_easy | saas_medium | saas_hard | Mean Avg Score | Mean Success Rate | Mean Avg Turns | Mean Invalid Action Rate |
|------|------|-----------|-------------|-----------|----------------|-------------------|----------------|--------------------------|
| `qwen2.5:1.5b` | 10 | 0.4250 | 0.4000 | 0.5000 | 0.4417 | 0.0000 | 12.6667 | 0.8158 |

This result is useful because it is both weak and stable. The model can begin
the right workflow and sometimes find the right account or transaction, but it
still fails to reliably finish grounded ticket handling and spends too many
actions on invalid or redundant steps.

## Current observed small-model behavior

The first local `qwen2.5:1.5b` baseline run already shows a meaningful pattern:

- the model can often start the right workflow
- it can retrieve account and transaction information
- it can sometimes issue the correct refund
- it still struggles with grounded ticket handling
- it often loops on search actions and racks up invalid-action penalties

That is exactly the kind of behavior we want a benchmark to expose, because it
creates a measurable gap for fine-tuning.

## SaaS SFT data design

The SFT pipeline uses deterministic expert traces. Each dataset row captures:

- task ID
- step index
- prompt messages up to the current observation
- current observation text
- expected JSON action
- resulting observation
- reward
- terminal flag
- terminal grader score

This makes the dataset useful for training a model to predict the next correct
tool action from the current state.

## Expert policy design

The expert trajectories are not free-form text completions. They are explicit,
grounded tool-use sequences that match the environment contract.

Examples:

- easy:
  - search the correct billing ticket
  - close the correct ticket
- medium:
  - account review
  - transaction review
  - refund the correct duplicate
  - email the customer
  - close the ticket
- hard:
  - account review
  - transaction review
  - refund the correct duplicate
  - find the fraud ticket
  - escalate the fraud ticket
  - email the customer
  - close the resolved billing ticket

## Training workflow

The intended first training method is supervised fine-tuning, not RL.

Why:

- expert demonstrations already exist
- actions are structured JSON
- SFT is much simpler and cheaper to run locally
- it is enough to prove that the environment supports measurable improvement

The training path is:

1. generate expert traces
2. validate the dataset
3. fine-tune a small Qwen model with LoRA
4. export a new local Ollama model
5. rerun the same benchmark

## Comparison methodology

The comparison is only valid if all non-model variables are held fixed:

- same SaaS tasks
- same tool definitions
- same prompts
- same reward logic
- same graders
- same benchmark runner
- same repeat count

Only the model should change.

## Current training status

The first training run was a smoke test rather than a full benchmarked trained
model release. That smoke run completed the key pipeline stages:

- deterministic SaaS dataset generation
- dataset validation against current tool schemas
- LoRA smoke training for `Qwen/Qwen2.5-1.5B-Instruct`
- checkpoint output for later Ollama export and before/after benchmarking

Current smoke-run metadata:

| Base Model | Dataset Rows | Epochs | Learning Rate | Output |
|-----------|--------------|--------|---------------|--------|
| `Qwen/Qwen2.5-1.5B-Instruct` | 140 | 1 | 0.0002 | `artifacts/checkpoints/qwen25_saas_sft_smoke/` |

That means the project now has:

- a reproducible baseline summary
- a reproducible SaaS SFT dataset
- a completed local smoke checkpoint
- a ready comparison path for the next day's trained-model benchmark

## What counts as proof

For a credible hackathon or docs-page narrative, the important proof artifacts are:

- aggregate benchmark summary for the base model
- aggregate benchmark summary for the trained model
- comparison summary with metric deltas

Large raw outputs such as:

- full run logs
- datasets
- checkpoints
- local SQLite files

should remain generated artifacts rather than committed repo files.

## End-of-day verification snapshot

At the end of this work session, the repo-level checks most relevant to the
SaaS benchmark story passed locally:

- `75 passed` unit tests
- `28 passed` integration tests
- benchmark summary files written for the 10-run Qwen baseline
- SaaS SFT smoke checkpoint written successfully

The remaining benchmark step is to export the trained adapter into Ollama and
rerun the exact same SaaS benchmark procedure for the trained model.
