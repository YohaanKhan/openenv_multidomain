---
title: Multi-Domain LLM Evaluation Environment
emoji: "🎫"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
tags:
  - openenv
---

# Multi-Domain LLM Evaluation Environment

## Documentation: https://openenv-multidomain-docs.vercel.app/

A domain-pluggable OpenEnv environment for evaluating LLM agents on real-world professional workflows. Switch the active domain with one environment variable - same container, same API, same baseline script.

## Why This Exists

Most LLM evaluation focuses on knowledge retrieval or reasoning puzzles. Real-world agents need to orchestrate tools, track multi-step state, and handle ambiguous situations - the skills SaaS support agents, HR assistants, and legal reviewers use every day. This environment fills that gap.

## Quick Start

```bash
docker build -f server/Dockerfile -t multidomain-env .
docker run -p 7860:7860 -e DOMAIN=saas multidomain-env
```

## Domains

| Domain | Description | Tools | Tasks |
|--------|-------------|-------|-------|
| `saas` | SaaS customer support - triage, refund, escalate | 7 | 3 |
| `hr` | HR policy and leave management | 7 | 3 |
| `legal` | Contract review and risk flagging | 7 | 3 |

Switch with: `DOMAIN=hr docker run ...`

## Action Space

All domains use the same action type:

```json
{
  "tool_name": "search_tickets",
  "tool_args": {"query": "billing", "customer_id": "C-1042"},
  "thought": "Agent's reasoning - logged but not executed"
}
```

## Observation Space

```json
{
  "content": "Tool result text or initial task description",
  "done": false,
  "reward": 0.05,
  "info": {
    "step_count": 1,
    "task_id": "saas_easy",
    "trace_id": "uuid",
    "grader_score": null
  }
}
```

`grader_score` is populated only on the terminal step (`done=true`).

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Start new episode |
| `/step` | POST | Execute one action |
| `/state` | GET | Current episode metadata |
| `/tasks` | GET | List tasks + action schema |
| `/baseline` | POST | Run baseline agent (`OPENAI_API_KEY` required) |
| `/grader` | POST | Score a trajectory |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

## Tasks

### SaaS Domain

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `saas_easy` | Easy | Resolve billing ticket | 6 |
| `saas_medium` | Medium | Double charge refund | 12 |
| `saas_hard` | Hard | VIP multi-ticket triage | 20 |

### HR Domain

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `hr_easy` | Easy | Leave entitlement query | 5 |
| `hr_medium` | Medium | File leave request | 12 |
| `hr_hard` | Hard | Payroll dispute resolution | 18 |

### Legal Domain

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `legal_easy` | Easy | NDA termination clause review | 6 |
| `legal_medium` | Medium | Vendor contract payment terms | 12 |
| `legal_hard` | Hard | SaaS agreement multi-party review | 20 |

## Baseline Scores (`gpt-4o-mini`, temperature=0, `response_format="json_object"`)

Baseline scores are **deterministic** at temperature=0. All graders return scores in the range [0.0, 1.0].

### Competition Baseline (`inference.py`)

Required environment variables:
- `OPENAI_API_KEY` – Your OpenAI API key (or compatible provider key)
- `API_BASE_URL` – LLM endpoint (default: `https://api.openai.com/v1`)
- `MODEL_NAME` – Model identifier (default: `gpt-4o-mini`)
- `HF_SPACE_URL` – Deployed Space URL (default: `http://localhost:7860`)
- `DOMAIN` – Which domain to run (`saas` | `hr` | `legal`)

```bash
# Run locally against a live Docker container
OPENAI_API_KEY=sk-... API_BASE_URL=https://api.openai.com/v1 MODEL_NAME=gpt-4o-mini \
DOMAIN=saas python inference.py

# Run against deployed Space
OPENAI_API_KEY=sk-... HF_SPACE_URL=https://yokohamas-openenv-multidomain.hf.space \
DOMAIN=saas python inference.py
```

Expected output: task-by-task scores and average per domain.

**How to run your own baseline:**

```bash
# Against local Docker
docker run -p 7860:7860 -e DOMAIN=saas multidomain-env &
OPENAI_API_KEY=sk-... DOMAIN=saas python inference.py

# Against deployed Space
OPENAI_API_KEY=sk-... HF_SPACE_URL=https://yokohamas-openenv-multidomain.hf.space \
DOMAIN=saas python inference.py

# With OpenAI-compatible providers (e.g., OpenRouter)
OPENAI_API_KEY=sk-or-v1-... API_BASE_URL=https://openrouter.ai/api/v1 \
MODEL_NAME=meta-llama/llama-3.1-70b-instruct DOMAIN=saas python inference.py
```

## Security & Fairness

### Grader Audit

All graders have been thoroughly tested for:
- ✅ **Determinism**: Same trajectory always produces same score (no randomness, no clock/time dependencies)
- ✅ **Bounds**: All scores clamped to [0.0, 1.0] before returning
- ✅ **Isolation**: Work correctly with `session=None` (no hidden state leakage)
- ✅ **Edge cases**: Tested on empty trajectories, partial trajectories, perfect trajectories, malformed inputs
- ✅ **No Exploits**: Score manipulation via contrived actions is impossible

### Comprehensive Test Coverage

Run all tests:
```bash
pytest tests/unit/ -v
```

**Test Results:** 79 tests, all passing
- 7 grader tests per domain (determinism, bounds, session isolation, edge cases)
- 15+ tool tests per domain (correct/incorrect arguments, DB state transitions)
- 5+ baseline integration tests

### Known Limitations

- Graders are heuristic-based (rule analysis, not semantic ML). Score distribution will differ from human raters.
- LLM graders require live API calls (`/grader` with session; skipped if falsy)
- Max 20 steps per task (agents hitting this limit are marked done but may have suboptimal scores)

### Baseline Results

#### Llama 3.1 70B via OpenRouter (OpenAI-compatible API)

> [!NOTE]
> The public Hugging Face Space is currently configured to the `saas` domain by default. To evaluate other domains (`hr`, `legal`), run the environment locally or redeploy the Space with the `DOMAIN` environment variable updated.

| Domain | Easy   | Medium | Hard   | Average |
|--------|--------|--------|--------|---------|
| `saas` | 0.7500 | 0.7500 | 0.6750 | **0.7250** |

**Test Configuration:**
- Model: `meta-llama/llama-3.1-70b-instruct` via OpenRouter
- Temperature: 0.0 (deterministic)
- Response Format: JSON
- Deployment: HuggingFace Space (https://yokohamas-openenv-multidomain.hf.space)

**Security Audit Results:**
- ✅ All 79 unit tests pass
- ✅ Grader determinism verified (same trajectory → same score)
- ✅ Score clamping validated (all scores in [0.0, 1.0])
- ✅ No random/datetime dependencies (stateless)
- ✅ DB isolation tested (session=None handling)
- ✅ No exploitable edge cases detected

**Grading Method:** Each domain uses deterministic code graders (trajectory analysis) + optional LLM graders for tone/quality. Terminal score = average of all grader scores, clamped to [0.0, 1.0].

**Scoring Rubric** (per domain):
- **SaaS:** Ticket identification (20%), refund logic (20%), duplicate detection (20%), closure (20%), communication (20%)
- **HR:** Policy lookup (20%), leave balance (20%), request accuracy (20%), notification (20%), documentation (20%)
- **Legal:** Clause extraction (20%), risk assessment (20%), conflict detection (20%), memo docs (20%), recommendation quality (20%)

## Local Small-Model Benchmarking with Ollama

For local benchmarking and before-vs-after training comparisons, use the separate Ollama runner. This does not replace the competition baseline, but it is useful for showing how a smaller local model performs on the same SaaS tasks.

Start the environment:

```bash
DOMAIN=saas DATABASE_URL=sqlite:///./ollama_saas.db ./../venv/bin/python -m uvicorn server.app:app --port 7860
```

Run one local model:

```bash
./../venv/bin/python benchmarks/run_saas_ollama.py \
  --model codellama \
  --base-url http://localhost:7860 \
  --output-json benchmark_results/codellama_saas.json
```

Compare a base model and a trained variant:

```bash
./../venv/bin/python benchmarks/run_saas_ollama.py \
  --model codellama \
  --compare-model codellama-saas-ft \
  --base-url http://localhost:7860 \
  --output-json benchmark_results/codellama_compare.json
```

The Ollama runner reports:
- per-task grader score
- average score
- success rate
- average turns
- invalid action rate

Current local SaaS baseline (`qwen2.5:1.5b`, 10 repeated runs):

| Model | Runs | Easy | Medium | Hard | Mean Avg Score | Mean Success Rate | Mean Avg Turns | Mean Invalid Action Rate |
|------|------|------|--------|------|----------------|-------------------|----------------|--------------------------|
| `qwen2.5:1.5b` | 10 | 0.4250 | 0.4000 | 0.5000 | 0.4417 | 0.0000 | 12.6667 | 0.8158 |

This baseline is intentionally weak but informative: the model often starts the correct support workflow, but still loops heavily and accumulates invalid tool calls, which makes it a useful "before training" checkpoint for the SaaS domain.

For more credible benchmark evidence, run repeated evaluations and save all artifacts:

```bash
./../venv/bin/python benchmarks/run_saas_ollama.py \
  --model codellama \
  --compare-model codellama-saas-ft \
  --base-url http://localhost:7860 \
  --repeats 10 \
  --output-dir benchmark_results/codellama_vs_ft \
  --output-json benchmark_results/codellama_vs_ft_summary.json
```

This writes:
- one JSON file per run for the primary model
- one JSON file per run for the comparison model
- a `summary.json` aggregate file with mean metrics and deltas

Suggested reporting metrics:
- mean average score
- mean success rate
- mean average turns
- mean invalid action rate
- task-level score means for `saas_easy`, `saas_medium`, and `saas_hard`

## Adding a New Domain

```bash
bash scripts/new_domain.sh finance
# Fill in the 6 stub files - zero engine changes needed
```

## Setup

```bash
pip install openenv-core
DOMAIN=saas openenv validate --verbose
docker build -f server/Dockerfile -t multidomain-env .
DOMAIN=saas docker run -p 7860:7860 multidomain-env
```

