# AGENTS.md

## Project Overview

This project builds a **multi-domain OpenEnv environment framework**.

Goal:

* Create realistic environments (SaaS, HR, Legal)
* Evaluate agents via tool usage, reasoning, and task completion
* Maintain strict determinism and reproducibility

---

## Core Architecture

* server/ → environment engine (NO domain logic)
* domains/ → all business logic (plugins)
* each domain implements BaseDomain
* DomainRegistry dynamically loads domains

---

## Execution Model

Environment follows OpenEnv loop:

reset() → initial observation
step(action) → observation + reward + done

State is persisted via database (SQLAlchemy).

---

## Tool System

* Tools are pure functions
* Signature: (args, session) → str
* Must NEVER return dicts or objects
* Must NEVER raise exceptions

---

## Database Rules

* Always use session (no direct engine usage)
* Always call session.flush() after writes
* Never commit manually

---

## Determinism

* All seeds must be deterministic
* No randomness unless explicitly required
* Same task_id must always produce same state

---

## Graders

Two types:

* Code graders (deterministic)
* LLM graders (optional)

Graders must:

* accept (trajectory, session)
* return score ∈ [0, 1]

---

## Critical Constraints

* server/ MUST NOT import domains/
* All domain logic stays inside domains/
* Adding a new domain must require ZERO server changes

---

## What to Optimize For

* correctness over cleverness
* deterministic behavior
* modularity
* readability

---

## What to Avoid

* hidden state
* side effects outside DB
* breaking OpenEnv contract
* over-engineering early
