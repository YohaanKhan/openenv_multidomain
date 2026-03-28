openenv_multidomain/                    # OpenEnv package root
│
├── _init_.py                         # Exports: EnvAction, EnvObservation, MultiDomainEnv
├── models.py                           # Domain-agnostic Action + Observation (OpenEnv types)
├── client.py                           # EnvClient subclass
├── openenv.yaml                        # Manifest — lists tasks from ALL domains
├── pyproject.toml
├── uv.lock
├── README.md
├── baseline.py                         # OpenAI baseline — runs all 3 domains × 3 tasks
│
├── server/                             # Core engine — zero domain knowledge here
│   ├── _init_.py
│   ├── app.py                          # create_app(factory, ...) + /tasks /baseline /grader
│   ├── environment.py                  # MultiDomainEnvironment: reset(), step(), state
│   ├── interfaces.py                   # ABCs: BaseDomain, BaseTool, BaseGrader
│   ├── domain_registry.py             # DomainRegistry singleton
│   ├── system_prompt_builder.py       # Builds prompt purely from domain.get_tools() schemas
│   ├── Dockerfile
│   ├── requirements.txt
│   └── utils/
│       ├── db.py                       # TransactionManager (per-domain schema, savepoints)
│       ├── logger.py                   # JSON logging + trace_id via contextvars
│       ├── metrics.py                  # Prometheus counters
│       └── replay.py                  # Trajectory replay from JSONL
│
├── domains/                            # Domain plugins — each is a self-contained package
│   ├── _init_.py                     # Auto-imports all domains to trigger registration
│   │
│   ├── saas/                           # Domain 1: SaaS Customer Support
│   │   ├── _init_.py                 # DomainRegistry.register("saas", SaaSDomain)
│   │   ├── domain.py                   # SaaSDomain(BaseDomain)
│   │   ├── schema.py                   # SQLAlchemy models for this domain's DB tables
│   │   ├── tasks.py                    # 3 tasks: easy / medium / hard + seed data
│   │   ├── prompts.py                  # System prompt template for this domain
│   │   ├── tools/
│   │   │   ├── definitions.py          # Pydantic arg schemas (what the LLM sees)
│   │   │   └── implementation.py       # Pure functions(validated_args, session) → str
│   │   └── graders/
│   │       ├── code_grader.py          # Deterministic: checks tool call sequence + state
│   │       └── llm_grader.py           # LLM-as-judge: evaluates response quality
│   │
│   ├── hr/                             # Domain 2: HR Policy & Onboarding
│   │   ├── _init_.py                 # DomainRegistry.register("hr", HRDomain)
│   │   ├── domain.py
│   │   ├── schema.py
│   │   ├── tasks.py
│   │   ├── prompts.py
│   │   ├── tools/
│   │   │   ├── definitions.py
│   │   │   └── implementation.py
│   │   └── graders/
│   │       ├── code_grader.py
│   │       └── llm_grader.py
│   │
│   └── legal/                          # Domain 3: Contract Review
│       ├── _init_.py                 # DomainRegistry.register("legal", LegalDomain)
│       ├── domain.py
│       ├── schema.py
│       ├── tasks.py
│       ├── prompts.py
│       ├── tools/
│       │   ├── definitions.py
│       │   └── implementation.py
│       └── graders/
│           ├── code_grader.py
│           └── llm_grader.py
│
├── scripts/
│   ├── new_domain.sh                   # Scaffold a new domain in < 30 seconds
│   └── replay.py                       # CLI: python replay.py --trace <id>
│
└── tests/
    ├── unit/                           # Tool + grader tests per domain
    ├── integration/                    # Full episode tests (in-memory DB, test domain)
    └── e2e/        


# ARCHITECTURE.md

## High-Level Design

Multi-domain environment system built on OpenEnv.

---

## Core Components

### 1. Environment

* Handles reset() and step()
* Delegates logic to active domain

---

### 2. Domain

Each domain provides:

* tools
* tasks
* graders
* seed data
* prompt template

---

### 3. Tools

* Represent actions agent can take
* Operate on DB state

---

### 4. Database

* Shared across domains
* Isolated via transactions

---

### 5. Graders

* Evaluate trajectory
* Provide reward signals

---

## Data Flow

Agent → Action → Tool → DB → Result → Reward → Observation

---

## Design Philosophy

* modular
* deterministic
* extensible
* testable
