# Deployment and Validation

## Validation philosophy

This project is not only a codebase; it is a submission artifact. That means
the environment must prove:

- spec compliance
- reproducibility
- deployment readiness
- baseline execution readiness

## OpenEnv compliance

The repo includes:

- typed action and observation models
- `reset()`, `step()`, and `state()`
- `openenv.yaml`
- deterministic task grading
- `/tasks`, `/grader`, and `/baseline` endpoints

`openenv validate` is part of the standard verification path.

## Docker and Spaces readiness

The Docker setup is aligned to Hugging Face Spaces requirements:

- app runs on port `7860`
- health checks target `7860`
- runtime uses a writable SQLite path (`/tmp/env.db`) by default inside the container
- image files are owned by the non-root Spaces user (`uid 1000`)
- Docker build has been verified locally
- container smoke tests cover the expected endpoints

This is critical because deployment failure is a disqualifying condition in the
hackathon brief.

## Test coverage

The repository now includes:

- unit tests for domain tool behavior
- unit tests for grader determinism and score ranges
- integration tests for full in-process episodes
- e2e container smoke tests
- benchmark utility tests
- SaaS SFT data/comparison utility tests

This gives coverage at several levels:

- logic
- environment behavior
- deployment behavior
- benchmark tooling

## Benchmark evidence workflow

There are now two benchmark stories in the repo:

### Submission baseline

- OpenAI baseline via `baseline.py`
- required for hackathon compliance

### Local benchmark story

- Ollama benchmark runner
- repeated-run local evaluation
- before/after training comparison

The local story is not a replacement for the submission baseline; it is a
supporting evaluation narrative for a small model.

## Recommended docs-page narrative

If this material is reused in a public docs page later, the strongest sequence is:

1. explain the real-world utility gap
2. show the multi-domain architecture
3. show the shared API and deterministic grading
4. spotlight the SaaS domain as the benchmark/training domain
5. show a small-model baseline
6. show expert-trace SFT
7. show before/after benchmark deltas

That tells a coherent story:

- environment design
- training utility
- measurable model improvement

## Operational note

Long-running local jobs such as:

- repeated Ollama benchmark runs
- model downloads
- fine-tuning

should usually be run directly in the user’s own terminal rather than through
an assistant session, because direct terminal access makes progress easier to
observe and interrupt safely.
