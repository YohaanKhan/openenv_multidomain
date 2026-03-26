# Multi-Domain LLM Evaluation Environment

A domain-pluggable OpenEnv environment for evaluating LLM agents on real-world professional workflows.

**Switch domains with a single environment variable** — same container, same API, same baseline script.

---

## Why This Exists

Most LLM evaluation focuses on knowledge retrieval or reasoning puzzles.  
Real-world agents need to:

- Orchestrate tools
- Track multi-step state
- Handle ambiguity

This environment simulates real workflows like SaaS support, HR operations, and legal review.

---

## Quick Start

```bash
docker build -f server/Dockerfile -t multidomain-env .
docker run -p 7860:7860 -e DOMAIN=saas multidomain-env
```

---

## Domains

| Domain  | Description                      | Tools | Tasks |
|---------|----------------------------------|-------|-------|
| saas    | SaaS support: triage, refund, escalation | 7     | 3     |
| hr      | HR policy + leave workflows      | 7     | 3     |
| legal   | Contract review + risk detection | 7     | 3     |

**Switch domain:**
```bash
DOMAIN=hr docker run ...
```

---

## Action Space

```json
{
  "tool_name": "search_tickets",
  "tool_args": {
    "query": "billing",
    "customer_id": "C-1042"
  },
  "thought": "Agent reasoning (logged only)"
}
```

---

## Observation Space

```json
{
  "content": "Tool result or task description",
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

- `done = true` → episode finished  
- `grader_score` only appears at final step

---

## API Endpoints

| Endpoint    | Method   | Description                  |
|-------------|----------|------------------------------|
| `/reset`    | POST     | Start new episode            |
| `/step`     | POST     | Execute one action           |
| `/state`    | GET      | Current state                |
| `/tasks`    | GET      | Task list + schema           |
| `/baseline` | POST     | Run baseline agent           |
| `/grader`   | POST     | Score trajectory             |
| `/health`   | GET      | Health check                 |
| `/metrics`  | GET      | Prometheus metrics           |

---

## Tasks

### SaaS

| Task        | Difficulty | Objective                  | Max Steps |
|-------------|------------|----------------------------|-----------|
| saas_easy   | Easy       | Resolve billing issue      | 6         |
| saas_medium | Medium     | Handle double charge       | 12        |
| saas_hard   | Hard       | Multi-ticket VIP triage    | 20        |

### HR

| Task      | Difficulty | Objective            | Max Steps |
|-----------|------------|----------------------|-----------|
| hr_easy   | Easy       | Leave entitlement query | 5        |
| hr_medium | Medium     | Submit leave request | 12        |
| hr_hard   | Hard       | Payroll dispute      | 18        |

### Legal

| Task         | Difficulty | Objective                | Max Steps |
|--------------|------------|--------------------------|-----------|
| legal_easy   | Easy       | NDA clause review        | 6         |
| legal_medium | Medium     | Contract payment terms   | 12        |
| legal_hard   | Hard       | Multi-party SaaS agreement | 20      |

---

## Baseline

Run the baseline agent:

```bash
OPENAI_API_KEY=sk-... DOMAIN=saas python baseline.py
```

| Domain | Easy  | Medium | Hard  | Average |
|--------|-------|--------|-------|---------|
| saas   | TODO  | TODO   | TODO  | TODO    |
| hr     | TODO  | TODO   | TODO  | TODO    |
| legal  | TODO  | TODO   | TODO  | TODO    |

---

## Adding a New Domain

```bash
bash scripts/new_domain.sh finance
```

Fill in the generated stubs — no core changes required.

---

## Setup

```bash
pip install openenv-core
DOMAIN=saas openenv validate --verbose

docker build -f server/Dockerfile -t multidomain-env .
DOMAIN=saas docker run -p 7860:7860 multidomain-env
```

---

## License

MIT
```

This version is clean, scannable, and ready to drop into GitHub, HuggingFace Spaces, or any Markdown-supported platform.
