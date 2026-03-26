"""Validate generated SaaS SFT datasets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import domains  # noqa: F401
    from server.domain_registry import DomainRegistry
except ImportError:
    from openenv_multidomain import domains  # noqa: F401
    from openenv_multidomain.server.domain_registry import DomainRegistry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_path", help="Path to the generated JSONL dataset.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(dataset_path)

    domain = DomainRegistry.require("saas")()
    tools = domain.get_tools()
    tasks = {task["id"] for task in domain.get_tasks()}

    rows = 0
    seen_tasks: set[str] = set()
    terminal_scores: dict[str, int] = {}

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            payload = json.loads(line)
            rows += 1

            task_id = payload["task_id"]
            seen_tasks.add(task_id)
            if task_id not in tasks:
                raise ValueError(f"Unknown task_id on line {line_no}: {task_id}")

            action = payload["action"]
            tool_name = action["tool_name"]
            if tool_name not in tools:
                raise ValueError(f"Unknown tool on line {line_no}: {tool_name}")
            tools[tool_name]["schema"](**action["tool_args"])

            if not payload["observation"]:
                raise ValueError(f"Missing observation on line {line_no}")
            if "ASSISTANT:" not in payload["prompt"]:
                raise ValueError(f"Prompt format mismatch on line {line_no}")

            if payload["done"]:
                terminal_grader_score = payload["terminal_grader_score"]
                if terminal_grader_score is None or terminal_grader_score <= 0.0:
                    raise ValueError(
                        f"Terminal step must have non-zero grader score on line {line_no}"
                    )
                terminal_scores[task_id] = terminal_scores.get(task_id, 0) + 1

    missing_tasks = tasks - seen_tasks
    if missing_tasks:
        raise ValueError(f"Dataset missing tasks: {sorted(missing_tasks)}")

    summary = {
        "rows": rows,
        "tasks": sorted(seen_tasks),
        "terminal_examples": terminal_scores,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
