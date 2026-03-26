# Architecture

## High-level design

The project uses a plugin-style domain architecture on top of a shared OpenEnv
engine. The engine is responsible for:

- episode lifecycle
- prompt construction
- tool argument validation
- reward computation hooks
- trajectory logging
- grader invocation
- metrics and trace metadata

Each domain is responsible for:

- schema
- tool definitions
- tool implementations
- task seed data
- prompt template
- deterministic grader logic

## Core components

### Server and runtime

- `server/environment.py`
  - core environment implementation
  - handles `reset()`, `step()`, and state/trajectory tracking
- `server/app.py`
  - FastAPI/OpenEnv app wiring
  - exposes `/reset`, `/step`, `/state`, `/tasks`, `/grader`, `/baseline`, `/health`, `/metrics`
- `server/utils/db.py`
  - SQLAlchemy setup and transaction manager
  - uses per-episode transaction handling for deterministic resets
- `server/system_prompt_builder.py`
  - builds the task-facing prompt from the domain template and tool schemas

### Domain abstraction

- `server/interfaces.py`
  - `BaseDomain` and `BaseGrader` contracts
- `server/domain_registry.py`
  - plugin registration and lookup

Each domain package follows the same pattern:

- `schema.py`
- `tasks.py`
- `tools/definitions.py`
- `tools/implementation.py`
- `prompts.py`
- `graders/code_grader.py`
- `graders/llm_grader.py`
- `domain.py`

## Request/response lifecycle

### Reset flow

1. environment rolls back the previous episode transaction
2. environment creates a new episode ID and trace ID
3. environment selects the next task
4. domain seed logic inserts deterministic task data
5. system prompt is combined with the task description
6. initial observation is returned

### Step flow

1. action arrives with `tool_name`, `tool_args`, and `thought`
2. tool name is checked against the domain tool registry
3. tool args are validated against the Pydantic schema
4. tool function executes against the episode DB session
5. domain reward shaping computes step reward
6. domain `is_done()` decides whether the episode should terminate
7. step metadata is appended to the internal trajectory
8. if terminal, graders run and an aggregate score is returned in `info.grader_score`

## Why the plugin structure matters

The engine does not know domain-specific business logic. That keeps it stable
while allowing new domains to be added with:

- new tables
- new tools
- new tasks
- new graders

This gives the environment two important properties:

- extensibility without engine rewrites
- comparability across domains because the interface stays fixed

## SaaS-specific architectural note

The SaaS domain is now the benchmark showcase domain. Its domain package has
been upgraded with:

- richer schema fields
- larger deterministic background seed data
- more realistic tool outputs
- grounded grader logic keyed to correct IDs and workflow steps
- reward shaping tuned for billing/refund/escalation workflows

That means the benchmark complexity increased while preserving the same shared
environment contract.
