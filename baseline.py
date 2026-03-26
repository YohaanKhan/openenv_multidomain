"""OpenAI API baseline runner for the multidomain OpenEnv environment."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from openai import OpenAI

try:
    import domains  # noqa: F401
    from client import MultiDomainEnv
    from models import EnvAction
    from server.domain_registry import DomainRegistry
except ImportError:
    from . import domains  # noqa: F401
    from .client import MultiDomainEnv
    from .models import EnvAction
    from .server.domain_registry import DomainRegistry


def _extract_text(response: Any) -> str:
    """Return the first assistant message text from a Chat Completions response."""
    choice = response.choices[0].message
    content = choice.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        if text_parts:
            return "".join(text_parts)
    raise ValueError("OpenAI response did not contain text content.")


def _reset_for_task(env: Any, task_id: str, known_task_count: int) -> Any:
    """
    Reset the environment and align to the requested task when possible.

    The frozen server-side environment currently ignores `task_id` kwargs and
    rotates through tasks internally. We still pass `task_id=...` first in case
    that support is added later, then advance deterministically until the
    requested task appears in the reset observation metadata.
    """
    result = env.reset(task_id=task_id)
    observed_task_id = result.observation.info.get("task_id")
    if observed_task_id == task_id:
        return result

    for _ in range(max(known_task_count - 1, 0)):
        result = env.reset()
        observed_task_id = result.observation.info.get("task_id")
        if observed_task_id == task_id:
            return result

    raise RuntimeError(
        f"Could not align reset() to task '{task_id}'. Last observed task was "
        f"'{observed_task_id}'."
    )


def run_episode(env: Any, client: OpenAI, task_id: str, max_turns: int = 30) -> float:
    """Run a single episode for one task and return the terminal grader score."""
    initial = _reset_for_task(env, task_id, known_task_count=3)
    observation = initial.observation
    done = initial.done
    turns = 0

    messages: list[dict[str, str]] = [{"role": "user", "content": observation.content}]

    while not done and turns < max_turns:
        turns += 1
        response = client.chat.completions.create(
            model=os.getenv("BASELINE_MODEL", "gpt-4o-mini"),
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        raw = _extract_text(response)
        action_dict = json.loads(raw)
        action = EnvAction(
            tool_name=action_dict.get("tool_name", ""),
            tool_args=action_dict.get("tool_args", {}),
            thought=action_dict.get("thought", ""),
        )

        step_result = env.step(action)
        observation = step_result.observation
        done = step_result.done

        print(f"[turn {turns}] tool={action.tool_name} reward={step_result.reward}")

        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": observation.content})

    return float(observation.info.get("grader_score", 0.0))


def run_baseline_all(domain_name: str) -> dict[str, float]:
    """Run one episode per task for the selected domain and return task scores."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is required to run the baseline agent."
        )

    client = OpenAI(api_key=api_key)
    domain = DomainRegistry.require(domain_name)()
    tasks = domain.get_tasks()
    base_url = os.getenv("HF_SPACE_URL", "http://localhost:7860")

    scores: dict[str, float] = {}
    with MultiDomainEnv(base_url=base_url) as env:
        for task in tasks:
            print(
                f"Running [{domain_name}] task: {task['id']} ({task['difficulty']})"
            )
            score = run_episode(env, client, task["id"])
            rounded = round(score, 4)
            scores[task["id"]] = rounded
            print(f"Score: {rounded:.4f}")

    return scores


def _print_results(domain_name: str, scores: dict[str, float]) -> None:
    """Print a compact results table with the average score."""
    print(f"Baseline Results ({domain_name})")
    for task_id, score in scores.items():
        print(f"{task_id:<20} {score:.4f}")
    average = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"{'AVERAGE':<20} {average:.4f}")


def main() -> None:
    """CLI entrypoint for running the OpenAI baseline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--domain",
        choices=DomainRegistry.list_domains(),
        default=os.getenv("DOMAIN", "saas"),
    )
    args = parser.parse_args()

    scores = run_baseline_all(args.domain)
    _print_results(args.domain, scores)


if __name__ == "__main__":
    main()
