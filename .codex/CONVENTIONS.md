# CONVENTIONS.md

## OpenEnv Rules

* reset() returns Observation
* step() returns Observation
* reward is inside Observation

---

## Tool Conventions

* return type: string ONLY
* never return JSON objects
* must be human-readable

---

## Naming

* snake_case for functions
* PascalCase for classes
* clear, descriptive names

---

## Error Handling

* never raise exceptions to agent
* always return error string

---

## Database

* use session everywhere
* always flush after write

---

## Prompting

* do NOT duplicate tool schema in prompt
* use {tool_docs}

---

## Simplicity Rule

If a solution feels complex, simplify it
