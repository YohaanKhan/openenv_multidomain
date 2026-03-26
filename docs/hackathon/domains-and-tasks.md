# Domains and Tasks

## Overview

The project currently ships with three domains. Each domain has exactly three
tasks with increasing difficulty:

- easy
- medium
- hard

All tasks are deterministic. The environment seeds the same initial state for a
given task ID, which makes grading and benchmarking reproducible.

## SaaS domain

### Real-world focus

The SaaS domain simulates support and billing workflows:

- ticket search
- account review
- transaction review
- refund handling
- ticket escalation
- customer communication
- ticket closure

### Current task design

#### `saas_easy`

Resolve a billing issue by identifying the correct customer ticket among
realistic distractors and closing the verified target ticket.

#### `saas_medium`

Handle a duplicate-charge complaint by:

- reviewing the account
- reviewing transactions
- refunding the correct duplicate charge
- emailing the customer
- closing the related billing ticket

#### `saas_hard`

Handle a VIP multi-step billing incident by:

- reviewing the VIP account
- reviewing transactions
- refunding the correct duplicate charge
- identifying the fraud-related ticket
- escalating the fraud issue
- notifying the customer
- closing only the resolved billing ticket

### Why SaaS is the benchmark domain

The SaaS domain has been upgraded to be the best training/evaluation target in
the repo. It now includes:

- richer schema fields
- larger seeded background data
- multiple distractor records
- realistic account/ticket/transaction relationships
- stronger grader logic tied to correct IDs

This makes it a good candidate for:

- before/after small-model benchmarking
- expert-trace generation
- supervised fine-tuning experiments

## HR domain

### Real-world focus

The HR domain models:

- policy lookup
- leave balances
- employee record inspection
- benefits information
- internal request filing and closure

### Task progression

- easy: leave/policy retrieval
- medium: filing and completing a leave workflow
- hard: a multi-step HR resolution flow using generated request references

The hard task specifically tests information chaining, because the model must
reuse a generated request reference correctly.

## Legal domain

### Real-world focus

The legal domain models:

- section retrieval
- clause comparison
- risk flagging
- standard-term comparison
- memo note creation
- memo finalization

### Task progression

- easy: targeted clause/memo workflow
- medium: compare and assess contract language
- hard: multi-step review with risk flagging and final memo output

## Difficulty philosophy

Difficulty is not just about more steps. It also comes from:

- distractor records
- partial information
- ambiguity
- grounded ID reuse
- workflow ordering
- domain-specific completion rules

The hard tasks are intended to expose where smaller models:

- choose the wrong record
- hallucinate IDs
- stop too early
- loop on search instead of grounding on retrieved outputs
