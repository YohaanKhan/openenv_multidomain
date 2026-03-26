# Environment API

## Shared action type

All domains use the same universal action schema:

```json
{
  "tool_name": "search_tickets",
  "tool_args": {
    "query": "renewal",
    "customer_id": "C-1042",
    "status": "open"
  },
  "thought": "Find the correct billing ticket before acting."
}
```

### Field meanings

- `tool_name`
  - the domain tool to execute
- `tool_args`
  - JSON object validated against the tool schema before execution
- `thought`
  - optional reasoning string that is logged but not executed

## Shared observation type

```json
{
  "content": "Tool result or initial task prompt",
  "done": false,
  "reward": 0.05,
  "info": {
    "step_count": 1,
    "task_id": "saas_easy",
    "task_difficulty": "easy",
    "trace_id": "uuid",
    "domain": "saas",
    "grader_score": null
  }
}
```

### Important metadata

- `step_count`
  - the current turn number in the episode
- `task_id`
  - the active task
- `trace_id`
  - episode trace identifier useful for logs and debugging
- `grader_score`
  - populated only on terminal observations

## API endpoints

### `/reset`

Starts a new episode and returns the initial observation.

### `/step`

Executes one validated tool call and returns:

- tool result text
- reward for the step
- `done`
- updated metadata

### `/state`

Returns the current environment state object, including episode ID and step count.

### `/tasks`

Returns:

- current domain
- available tasks
- action schema

### `/grader`

Scores a provided trajectory using the domain graders.

### `/baseline`

Runs the official OpenAI baseline for the current domain.

### `/health`

Simple health check for deployment and smoke testing.

## Reward model

Rewards are shaped at the domain layer. In SaaS, for example:

- valid lookup steps get small positive reward
- grounded refund/escalation/close steps get stronger positive reward
- invalid tools or missing records are penalized
- clearly wrong refund behavior is penalized more strongly

This provides a denser signal than terminal-only success while still preserving
clear task-level grading at episode end.

## Episode boundaries

Episodes terminate when:

- the domain decides the task is complete
- or the task step limit is reached

At termination:

- graders execute
- `grader_score` is attached to the final observation
- the episode transaction is rolled back for deterministic reset behavior
