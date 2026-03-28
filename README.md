---
title: Multi-Domain OpenEnv
emoji: 🎫
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
base_path: /web
pinned: false
tags:
  - openenv
---

# Multi-Domain LLM Evaluation Environment

An OpenEnv environment for evaluating LLM agents on real-world professional workflows. The same container, API, and inference script can run multiple domains by switching one environment variable.

## Links

- Docs: `https://openenv-multidomain-docs.vercel.app/`
- Live Hugging Face Space: `https://huggingface.co/spaces/Yokohamas/openenv_multidomain_v2`
- Live Web UI: `https://yokohamas-openenv-multidomain-v2.hf.space/web/`
- Live API base URL: `https://yokohamas-openenv-multidomain-v2.hf.space`

## What This Repo Covers

- `saas`: customer support workflows like billing triage, refunds, and escalation
- `hr`: leave management, payroll disputes, and policy workflows
- `legal`: contract review, clause extraction, and risk flagging

Each domain currently exposes 7 tools and 3 tasks.

## Quick Start

### Local Docker

```bash
docker build -t multidomain-env .
docker run -p 7860:7860 -e DOMAIN=saas multidomain-env
```

Switch domains with `DOMAIN=hr` or `DOMAIN=legal`.

### Local Validation

```bash
pip install openenv-core
DOMAIN=saas openenv validate --verbose
```

### Deployed Space

Open the live UI:

```text
https://yokohamas-openenv-multidomain-v2.hf.space/web/
```

Or use the API directly:

```bash
curl https://yokohamas-openenv-multidomain-v2.hf.space/health
curl https://yokohamas-openenv-multidomain-v2.hf.space/tasks
curl -X POST https://yokohamas-openenv-multidomain-v2.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Deployment Notes

For Hugging Face Spaces, the Docker image is set up to:

- run as UID `1000`
- copy files with the correct ownership
- store the SQLite runtime database at `/tmp/env.db`
- enable the browser UI at `/web`
- use `.dockerignore` so local artifacts, caches, tests, and DB files do not enter the Docker build context

When deploying with `openenv push`, use `.hfignore` so local artifacts are not uploaded:

```bash
openenv push . --repo-id Yokohamas/openenv_multidomain_v2 --exclude .hfignore
```

If you deploy by pushing the repository directly to a Docker Space, `.hfignore` is not enough by itself. Docker uses `.dockerignore` for build context filtering.

## Environment Contract

### Action Format

```json
{
  "tool_name": "search_tickets",
  "tool_args": {"query": "billing", "customer_id": "C-1042"},
  "thought": "Reasoning is logged but not executed"
}
```

### Observation Format

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

`grader_score` is only present on terminal observations.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tasks` | GET | Domain tasks and action schema |
| `/reset` | POST | Start a new episode |
| `/step` | POST | Execute one environment action |
| `/state` | GET | Current episode metadata |
| `/baseline` | POST | Run the built-in baseline agent |
| `/grader` | POST | Score a trajectory |
| `/metrics` | GET | Prometheus metrics |
| `/web/metadata` | GET | Web UI metadata |
| `/web/reset` | POST | Reset for the browser UI |
| `/web/step` | POST | Step for the browser UI |
| `/web/state` | GET | Browser UI state |

If you call the web endpoints manually, `/web/step` expects the payload shape `{"action": {...}}`.

## Domains And Tasks

### Domains

| Domain | Description | Tools | Tasks |
|--------|-------------|-------|-------|
| `saas` | SaaS customer support triage, refunds, escalation | 7 | 3 |
| `hr` | HR policy, leave management, payroll workflows | 7 | 3 |
| `legal` | Contract review and risk flagging | 7 | 3 |

### SaaS Tasks

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `saas_easy` | Easy | Resolve billing ticket | 6 |
| `saas_medium` | Medium | Double charge refund | 12 |
| `saas_hard` | Hard | VIP multi-ticket triage | 20 |

### HR Tasks

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `hr_easy` | Easy | Leave entitlement query | 5 |
| `hr_medium` | Medium | File leave request | 12 |
| `hr_hard` | Hard | Payroll dispute resolution | 18 |

### Legal Tasks

| Task | Difficulty | Objective | Max Steps |
|------|-----------|-----------|-----------|
| `legal_easy` | Easy | NDA termination clause review | 6 |
| `legal_medium` | Medium | Vendor contract payment terms | 12 |
| `legal_hard` | Hard | SaaS agreement multi-party review | 20 |

## Inference Guide

The competition/baseline runner is [inference.py](/Users/yohaankhan/Desktop/trialect/openenv_multidomain/inference.py). It drives the environment through the public API and prints task-by-task scores.

Required environment variables:

- `OPENAI_API_KEY`: OpenAI or OpenAI-compatible API key
- `API_BASE_URL`: LLM endpoint, default `https://api.openai.com/v1`
- `MODEL_NAME`: model id, default `gpt-4o-mini`
- `HF_SPACE_URL`: environment base URL, default `http://localhost:7860`
- `DOMAIN`: `saas`, `hr`, or `legal`

### Run Against Local Docker

```bash
docker run -p 7860:7860 -e DOMAIN=saas multidomain-env &
OPENAI_API_KEY=sk-... DOMAIN=saas python inference.py
```

### Run Against The Live HF Space

```bash
OPENAI_API_KEY=sk-... \
HF_SPACE_URL=https://yokohamas-openenv-multidomain-v2.hf.space \
DOMAIN=saas python inference.py
```

### OpenAI-Compatible Providers

OpenRouter example:

```bash
OPENAI_API_KEY=sk-or-v1-... API_BASE_URL=https://openrouter.ai/api/v1 \
MODEL_NAME=meta-llama/llama-3.1-70b-instruct \
HF_SPACE_URL=https://yokohamas-openenv-multidomain-v2.hf.space \
DOMAIN=saas python inference.py
```

Groq example:

```bash
OPENAI_API_KEY=gsk_... API_BASE_URL=https://api.groq.com/openai/v1 \
MODEL_NAME=llama-3.1-8b-instant \
HF_SPACE_URL=https://yokohamas-openenv-multidomain-v2.hf.space \
DOMAIN=saas python inference.py
```

Groq note:
- `llama-3.1-8b-instant` successfully completed the live `saas_easy` task during verification.
- `openai/gpt-oss-20b` was less reliable with this script because it sometimes attempted tool-calling instead of returning the strict JSON object `inference.py` expects.
- Longer Groq runs may hit `429` rate limits depending on account tier.

## Evaluation And Results

Baseline scores are deterministic at `temperature=0`. All grader outputs are clamped to `[0.0, 1.0]`.

> [!NOTE]
> The public Hugging Face Space is currently configured to the `saas` domain by default. To evaluate `hr` or `legal`, run the environment locally or redeploy the Space with a different `DOMAIN`.

### Public SaaS Baseline

| Domain | Easy | Medium | Hard | Average |
|--------|------|--------|------|---------|
| `saas` | 0.7500 | 0.7500 | 0.6750 | **0.7250** |

Configuration:

- Model: `meta-llama/llama-3.1-70b-instruct` via OpenRouter
- Temperature: `0.0`
- Response format: JSON
- Deployment: `https://yokohamas-openenv-multidomain-v2.hf.space`

Scoring rubric:

- SaaS: ticket identification, refund logic, duplicate detection, closure, communication
- HR: policy lookup, leave balance, request accuracy, notification, documentation
- Legal: clause extraction, risk assessment, conflict detection, memo quality, recommendation quality

Known limitations:

- Graders are heuristic and rule-based, not semantic ML judges
- LLM graders require live API access when used
- Agents that hit max-step limits terminate with potentially suboptimal scores

## Tests And Reliability

Current verification status:

- 79 unit tests passing
- 28 integration episode tests passing
- live HF Space API verified
- live `/web` UI verified

Run tests locally:

```bash
PYTHONPATH=. ./../venv/bin/pytest tests/unit -q
PYTHONPATH=. ./../venv/bin/pytest tests/integration/test_full_episodes.py -q
```

Grader audit coverage includes:

- determinism
- score bounds
- session isolation
- malformed and partial trajectories
- exploit resistance checks

## Local Small-Model Benchmarking

Use the Ollama runner for local, lower-cost before/after benchmarking on the SaaS domain.

Start the environment:

```bash
DOMAIN=saas DATABASE_URL=sqlite:///./ollama_saas.db \
./../venv/bin/python -m uvicorn server.app:app --port 7860
```

Run one local model:

```bash
./../venv/bin/python benchmarks/run_saas_ollama.py \
  --model codellama \
  --base-url http://localhost:7860 \
  --output-json benchmark_results/codellama_saas.json
```

Compare a base model and a fine-tuned variant:

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

For repeated evaluation with saved artifacts:

```bash
./../venv/bin/python benchmarks/run_saas_ollama.py \
  --model codellama \
  --compare-model codellama-saas-ft \
  --base-url http://localhost:7860 \
  --repeats 10 \
  --output-dir benchmark_results/codellama_vs_ft \
  --output-json benchmark_results/codellama_vs_ft_summary.json
```

## Extending The Environment

### Add A New Domain

```bash
bash scripts/new_domain.sh finance
```

Then fill in the generated domain files. The core environment engine does not need to change.
