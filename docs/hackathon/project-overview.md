# Project Overview

## What this project is

This repository implements a multi-domain OpenEnv environment for evaluating
tool-using language agents on real professional workflows. Instead of focusing
on static QA or puzzle-style reasoning, it evaluates whether a model can:

- understand a task brief
- choose the correct tool
- pass grounded arguments
- interpret tool outputs
- chain multiple actions correctly
- stop after the job is actually complete

The environment supports three domains:

- `saas`: customer support, billing, refunds, escalation, and customer communication
- `hr`: employee policy, leave, and internal request handling
- `legal`: contract review, clause comparison, memo drafting, and risk flagging

## Why it exists

Most LLM evaluation still over-indexes on retrieval and reasoning without
workflow execution. Real agent systems have to operate in constrained tool
spaces, maintain state across multiple steps, and handle ambiguity without
hallucinating IDs or actions. This project exists to measure that behavior.

The core value proposition is:

- one shared engine
- multiple realistic domains
- deterministic tasks and grading
- the same action/observation interface across workflows

That lets us compare model behavior across very different task families without
rewriting the environment layer each time.

## What makes it useful

- It is close to real support and operations work, not a toy environment.
- It supports stepwise reward shaping rather than terminal-only success.
- It exposes structured tool use, which is more realistic for agents than free-form answers.
- It supports both official submission baselines and local small-model benchmarking.
- It can be used both for evaluation and for dataset generation for fine-tuning.

## Current state

The repo now includes:

- the full multi-domain environment
- unit, integration, and e2e testing
- OpenEnv validation support
- an OpenAI baseline script for submission compliance
- an Ollama benchmark runner for local before/after model comparisons
- a SaaS SFT data/training pipeline built around deterministic expert trajectories

## How to think about the project

There are two layers:

1. The environment layer
- defines tasks, tools, rewards, episode boundaries, and graders

2. The model layer
- uses the environment to benchmark or train a model

This separation is intentional. The same SaaS benchmark can be used to:

- test an OpenAI baseline
- test a local Ollama model
- generate expert trajectories for supervised fine-tuning
- compare before/after training metrics
