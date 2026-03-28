# TASK_GUIDELINES.md

## How Tasks Are Written

Each task must include:

* file path
* clear goal
* constraints
* expected behavior
* verification steps

---

## Example Format

File: domains/hr/schema.py

Goal:
Implement SQLAlchemy models for HR domain.

Constraints:

* use shared Base
* follow naming rules

Verification:

* create tables
* insert sample data
* validate defaults

---

## Rule

Tasks must be:

* atomic
* testable
* deterministic
