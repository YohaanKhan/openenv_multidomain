"""Helpers for generating SaaS expert trajectories and SFT datasets."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import domains  # noqa: F401
    from client import MultiDomainEnv
    from models import EnvAction
    from server.domain_registry import DomainRegistry
except ImportError:
    from openenv_multidomain import domains  # noqa: F401
    from openenv_multidomain.client import MultiDomainEnv
    from openenv_multidomain.models import EnvAction
    from openenv_multidomain.server.domain_registry import DomainRegistry


DEFAULT_ENV_URL = "http://localhost:7860"
SFT_SYSTEM_INSTRUCTION = (
    "Reply with a single JSON object only. "
    'Use exactly: {"tool_name": str, "tool_args": object, "thought": str}. '
    "Use concrete IDs returned by prior tool outputs. Do not invent IDs."
)


EXPERT_EPISODES: dict[str, list[dict[str, Any]]] = {
    "saas_easy": [
        {
            "tool_name": "search_tickets",
            "tool_args": {"query": "renewal", "customer_id": "C-1042", "status": "open"},
            "thought": "Find the active renewal billing ticket for Jane Smith before taking any action.",
        },
        {
            "tool_name": "close_ticket",
            "tool_args": {
                "ticket_id": "T-5001",
                "resolution": (
                    "Reviewed the annual renewal discrepancy, confirmed the corrected billing "
                    "amount, and closed the resolved ticket."
                ),
            },
            "thought": "Close the verified billing ticket once the correct record is confirmed.",
        },
    ],
    "saas_medium": [
        {
            "tool_name": "get_account",
            "tool_args": {"customer_id": "C-2077"},
            "thought": "Review the customer account before handling a duplicate charge claim.",
        },
        {
            "tool_name": "get_transactions",
            "tool_args": {"customer_id": "C-2077", "limit": 10},
            "thought": "Inspect recent transactions to locate the duplicate November subscription charge.",
        },
        {
            "tool_name": "issue_refund",
            "tool_args": {
                "customer_id": "C-2077",
                "transaction_id": "TX-9002",
                "amount": 49.0,
                "reason": "Refunding the duplicate November Pro subscription charge.",
            },
            "thought": "Refund only the duplicate transaction after verifying the customer and amount.",
        },
        {
            "tool_name": "send_email",
            "tool_args": {
                "customer_id": "C-2077",
                "subject": "Refund processed for duplicate November charge",
                "body": (
                    "Hi Bob,\n\nWe confirmed that transaction TX-9002 was a duplicate November "
                    "subscription charge and processed a $49.00 refund. Your active subscription "
                    "remains unchanged.\n\nBest,\nSupport"
                ),
            },
            "thought": "Send the customer a confirmation before the final closure step.",
        },
        {
            "tool_name": "close_ticket",
            "tool_args": {
                "ticket_id": "T-5002",
                "resolution": "Duplicate November subscription charge refunded and customer notified by email.",
            },
            "thought": "Close the billing ticket after the refund and customer notification are complete.",
        },
    ],
    "saas_hard": [
        {
            "tool_name": "get_account",
            "tool_args": {"customer_id": "C-9001"},
            "thought": "Review the VIP enterprise account before handling the incident.",
        },
        {
            "tool_name": "get_transactions",
            "tool_args": {"customer_id": "C-9001", "limit": 10},
            "thought": "Identify the duplicate March subscription transaction for the VIP account.",
        },
        {
            "tool_name": "issue_refund",
            "tool_args": {
                "customer_id": "C-9001",
                "transaction_id": "TX-9802",
                "amount": 499.0,
                "reason": "Refunding the duplicate March enterprise subscription charge.",
            },
            "thought": "Refund the confirmed duplicate charge before closing the billing issue.",
        },
        {
            "tool_name": "search_tickets",
            "tool_args": {"query": "fraud", "customer_id": "C-9001", "status": "open"},
            "thought": "Locate the urgent fraud-related ticket that must be escalated for this VIP account.",
        },
        {
            "tool_name": "escalate_ticket",
            "tool_args": {
                "ticket_id": "T-8001",
                "tier": 2,
                "reason": "VIP enterprise customer reported suspicious duplicate billing activity requiring fraud review.",
            },
            "thought": "Escalate the fraud concern to Tier 2 instead of trying to resolve it directly.",
        },
        {
            "tool_name": "send_email",
            "tool_args": {
                "customer_id": "C-9001",
                "subject": "Update on duplicate charge and fraud review",
                "body": (
                    "Hello Alice Corp,\n\nWe refunded the duplicate March subscription charge "
                    "(TX-9802) and escalated the suspicious billing activity ticket to our Tier 2 "
                    "fraud team for immediate review. We will follow up as soon as the fraud review "
                    "is complete.\n\nBest,\nSupport"
                ),
            },
            "thought": "Notify the VIP customer about both the refund and the escalation before closing the billing ticket.",
        },
        {
            "tool_name": "close_ticket",
            "tool_args": {
                "ticket_id": "T-8002",
                "resolution": "Duplicate March subscription charge refunded and customer updated by email.",
            },
            "thought": "Close only the resolved billing ticket; leave the fraud ticket escalated.",
        },
    ],
}


def _reset_for_task(env: Any, task_id: str, known_task_count: int) -> Any:
    """Reset the environment and align to a requested task id."""
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
        f"Could not align reset() to task '{task_id}'. Last observed task was '{observed_task_id}'."
    )


def format_chat_example(messages: list[dict[str, str]]) -> str:
    """Format chat messages into a simple prompt string for SFT."""
    parts: list[str] = []
    for message in messages:
        role = message["role"].upper()
        parts.append(f"{role}:\n{message['content']}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def make_target_json(step: dict[str, Any]) -> str:
    """Serialize one expert action target deterministically."""
    payload = {
        "tool_name": step["tool_name"],
        "tool_args": step["tool_args"],
        "thought": step["thought"],
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def collect_expert_episode(env: Any, task_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collect one deterministic expert episode for a SaaS task."""
    steps = deepcopy(EXPERT_EPISODES[task_id])
    initial = _reset_for_task(env, task_id, known_task_count=3)
    observation = initial.observation
    messages = [
        {"role": "system", "content": SFT_SYSTEM_INSTRUCTION},
        {"role": "user", "content": observation.content},
    ]

    records: list[dict[str, Any]] = []
    for step_idx, step in enumerate(steps, start=1):
        prompt_messages = deepcopy(messages)
        action = EnvAction(
            tool_name=step["tool_name"],
            tool_args=step["tool_args"],
            thought=step["thought"],
        )
        result = env.step(action)
        next_observation = result.observation
        target_json = make_target_json(step)
        record = {
            "domain": "saas",
            "task_id": task_id,
            "step_idx": step_idx,
            "messages": prompt_messages,
            "prompt": format_chat_example(prompt_messages),
            "target": target_json,
            "action": json.loads(target_json),
            "observation": prompt_messages[-1]["content"],
            "result_observation": next_observation.content,
            "reward": result.reward,
            "done": result.done,
            "terminal_grader_score": next_observation.info.get("grader_score"),
            "trace_id": next_observation.info.get("trace_id"),
        }
        records.append(record)
        messages.append({"role": "assistant", "content": target_json})
        messages.append({"role": "user", "content": next_observation.content})
    return records, {
        "task_id": task_id,
        "steps": len(records),
        "final_score": records[-1]["terminal_grader_score"] if records else 0.0,
    }


def dataset_task_order() -> list[str]:
    return sorted(EXPERT_EPISODES.keys())


def generate_expert_dataset(
    base_url: str,
    repeats: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Generate the full SaaS SFT dataset by replaying expert policies."""
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    dataset_rows: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    with MultiDomainEnv(base_url=base_url).sync() as env:
        for repeat_idx in range(1, repeats + 1):
            for task_id in dataset_task_order():
                records, task_summary = collect_expert_episode(env, task_id)
                for row in records:
                    row["repeat_idx"] = repeat_idx
                dataset_rows.extend(records)
                run_summaries.append({"repeat_idx": repeat_idx, **task_summary})

    per_task_counts: dict[str, int] = {}
    for row in dataset_rows:
        per_task_counts[row["task_id"]] = per_task_counts.get(row["task_id"], 0) + 1

    summary = {
        "domain": "saas",
        "repeats": repeats,
        "rows": len(dataset_rows),
        "task_counts": per_task_counts,
        "runs": run_summaries,
        "system_instruction": SFT_SYSTEM_INSTRUCTION,
    }
    return dataset_rows, summary
