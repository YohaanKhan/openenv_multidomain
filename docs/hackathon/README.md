# Hackathon Docs Index

This folder is the long-form project documentation set for the multi-domain
OpenEnv environment. It is written to be reusable later in a docs site or
hackathon submission page.

## Recommended reading order

1. [`project-overview.md`](project-overview.md)
2. [`architecture.md`](architecture.md)
3. [`environment-api.md`](environment-api.md)
4. [`domains-and-tasks.md`](domains-and-tasks.md)
5. [`saas-benchmark-and-training.md`](saas-benchmark-and-training.md)
6. [`deployment-and-validation.md`](deployment-and-validation.md)

## What this docs set covers

- why the environment exists and what gap it fills
- how the engine, domain plugins, tasks, tools, prompts, and graders fit together
- the shared action/observation API used by all domains
- how the SaaS benchmark domain was made more realistic
- how local small-model benchmarking works with Ollama
- how the SaaS SFT workflow works from expert traces to re-benchmarking
- how deployment, validation, and Docker verification fit into the submission story
