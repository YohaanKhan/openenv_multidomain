"""Compare two aggregate SaaS benchmark summary JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_summary(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    primary = payload["primary"]["aggregate"]
    return primary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-json")
    args = parser.parse_args()

    baseline = _load_summary(args.baseline)
    candidate = _load_summary(args.candidate)

    metrics = (
        "mean_average_score",
        "mean_success_rate",
        "mean_average_turns",
        "mean_invalid_action_rate",
    )
    delta = {
        metric: round(candidate[metric] - baseline[metric], 4)
        for metric in metrics
    }

    task_ids = sorted(
        set(baseline.get("task_score_means", {}).keys())
        | set(candidate.get("task_score_means", {}).keys())
    )
    task_deltas = {
        task_id: round(
            candidate.get("task_score_means", {}).get(task_id, 0.0)
            - baseline.get("task_score_means", {}).get(task_id, 0.0),
            4,
        )
        for task_id in task_ids
    }

    payload = {
        "baseline": baseline,
        "candidate": candidate,
        "delta": delta,
        "task_deltas": task_deltas,
    }
    print(json.dumps(payload, indent=2))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
