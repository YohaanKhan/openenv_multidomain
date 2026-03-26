"""Run local Ollama models against the SaaS benchmark domain.

This script is intentionally separate from `baseline.py` so the submission
baseline stays compliant with the OpenAI API requirement while local benchmark
experiments can use Ollama models such as CodeLlama.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import http.client
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request
from datetime import datetime, timezone


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


OLLAMA_CHAT_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434") + "/api/chat"
DEFAULT_ENV_URL = os.getenv("HF_SPACE_URL", "http://localhost:7860")
SUCCESS_THRESHOLD = float(os.getenv("BENCHMARK_SUCCESS_THRESHOLD", "0.8"))


@dataclass
class EpisodeStats:
    task_id: str
    score: float
    turns: int
    invalid_actions: int
    total_actions: int
    error: str = ""

    @property
    def success(self) -> bool:
        return self.score >= SUCCESS_THRESHOLD

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "score": round(self.score, 4),
            "turns": self.turns,
            "invalid_actions": self.invalid_actions,
            "total_actions": self.total_actions,
            "success": self.success,
            "error": self.error,
        }


def _extract_ollama_text(payload: dict[str, Any]) -> str:
    """Return assistant content from an Ollama chat response."""
    message = payload.get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    raise ValueError(f"Ollama response did not include assistant text: {payload}")


def _coerce_action_dict(raw_text: str) -> dict[str, Any]:
    """Parse a model reply into the action JSON shape expected by the env."""
    text = raw_text.strip()
    start = text.find("{")
    if start == -1:
        raise ValueError(f"Model reply did not contain JSON: {raw_text}")
    
    # Try to parse JSON starting from the first {, stopping as soon as we have valid JSON
    for end in range(start + 1, len(text) + 1):
        candidate = text[start:end]
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return {
                    "tool_name": str(payload.get("tool_name", "")),
                    "tool_args": payload.get("tool_args", {}) or {},
                    "thought": str(payload.get("thought", "")),
                }
        except json.JSONDecodeError:
            continue
    
    # Fallback: try the last } as before
    end = text.rfind("}")
    if end == -1 or end < start:
        raise ValueError(f"Model reply did not contain valid JSON: {raw_text}")
    
    try:
        payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError(f"Model reply was not a JSON object: {payload}")
        return {
            "tool_name": str(payload.get("tool_name", "")),
            "tool_args": payload.get("tool_args", {}) or {},
            "thought": str(payload.get("thought", "")),
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model reply: {str(e)}\nRaw: {raw_text}") from e


def _ollama_chat(
    model: str, messages: list[dict[str, str]], timeout: int = 120, retries: int = 3
) -> str:
    """Call the local Ollama chat endpoint and return assistant text."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                },
            }
        ).encode("utf-8")
        req = request.Request(
            OLLAMA_CHAT_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _extract_ollama_text(payload)
        except (error.URLError, http.client.RemoteDisconnected) as exc:
            last_exc = exc
            if attempt == retries:
                break
    raise RuntimeError(
        f"Failed to reach Ollama at {OLLAMA_CHAT_URL} after {retries} attempts."
    ) from last_exc


def _reset_for_task(env: Any, task_id: str, known_task_count: int) -> Any:
    """Reset the environment and align to the requested task."""
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


def run_episode(
    env: Any,
    model: str,
    task_id: str,
    max_turns: int = 30,
) -> EpisodeStats:
    """Run one SaaS episode with an Ollama model."""
    try:
        initial = _reset_for_task(env, task_id, known_task_count=3)
        observation = initial.observation
        done = initial.done
        turns = 0
        invalid_actions = 0

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Reply with a single JSON object only. "
                    'Use exactly: {"tool_name": str, "tool_args": object, "thought": str}. '
                    "Use concrete IDs returned by prior tool outputs. Do not invent IDs."
                ),
            },
            {"role": "user", "content": observation.content},
        ]

        while not done and turns < max_turns:
            turns += 1
            raw = _ollama_chat(model=model, messages=messages)
            action_dict = _coerce_action_dict(raw)
            action = EnvAction(
                tool_name=action_dict["tool_name"],
                tool_args=action_dict["tool_args"],
                thought=action_dict["thought"],
            )

            step_result = env.step(action)
            observation = step_result.observation
            done = step_result.done

            if step_result.reward < 0:
                invalid_actions += 1

            print(
                f"[{model}] [turn {turns}] task={task_id} tool={action.tool_name} "
                f"reward={step_result.reward}"
            )

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": observation.content})

        return EpisodeStats(
            task_id=task_id,
            score=float(observation.info.get("grader_score", 0.0)),
            turns=turns,
            invalid_actions=invalid_actions,
            total_actions=turns,
        )
    except Exception as exc:
        print(f"[{model}] task={task_id} failed: {exc}")
        return EpisodeStats(
            task_id=task_id,
            score=0.0,
            turns=0,
            invalid_actions=1,
            total_actions=1,
            error=str(exc),
        )


def run_model_suite(
    model: str,
    domain_name: str = "saas",
    base_url: str = DEFAULT_ENV_URL,
    max_turns: int = 30,
) -> tuple[dict[str, Any], list[EpisodeStats]]:
    """Run all tasks for one model and return aggregate metrics."""
    domain = DomainRegistry.require(domain_name)()
    tasks = domain.get_tasks()

    episodes: list[EpisodeStats] = []
    with MultiDomainEnv(base_url=base_url).sync() as env:
        for task in tasks:
            print(f"Running [{model}] task: {task['id']} ({task['difficulty']})")
            episodes.append(
                run_episode(env=env, model=model, task_id=task["id"], max_turns=max_turns)
            )

    return _summarize_runs(model, episodes), episodes


def _summarize_runs(model: str, episodes: list[EpisodeStats]) -> dict[str, Any]:
    """Aggregate per-episode metrics into a benchmark summary."""
    if not episodes:
        return {
            "model": model,
            "task_scores": {},
            "average_score": 0.0,
            "success_rate": 0.0,
            "average_turns": 0.0,
            "invalid_action_rate": 0.0,
        }

    total_actions = sum(ep.total_actions for ep in episodes) or 1
    task_scores = {ep.task_id: round(ep.score, 4) for ep in episodes}
    return {
        "model": model,
        "task_scores": task_scores,
        "average_score": round(sum(ep.score for ep in episodes) / len(episodes), 4),
        "success_rate": round(sum(1 for ep in episodes if ep.success) / len(episodes), 4),
        "average_turns": round(sum(ep.turns for ep in episodes) / len(episodes), 4),
        "invalid_action_rate": round(
            sum(ep.invalid_actions for ep in episodes) / total_actions, 4
        ),
    }


def _print_summary(summary: dict[str, Any]) -> None:
    print("")
    print(f"Ollama SaaS Benchmark Results ({summary['model']})")
    for task_id, score in summary["task_scores"].items():
        print(f"{task_id:<20} {score:.4f}")
    print(f"{'AVERAGE_SCORE':<20} {summary['average_score']:.4f}")
    print(f"{'SUCCESS_RATE':<20} {summary['success_rate']:.4f}")
    print(f"{'AVERAGE_TURNS':<20} {summary['average_turns']:.4f}")
    print(f"{'INVALID_RATE':<20} {summary['invalid_action_rate']:.4f}")


def _print_comparison(baseline_summary: dict[str, Any], candidate_summary: dict[str, Any]) -> None:
    print("")
    print("Comparison")
    metrics = (
        "average_score",
        "success_rate",
        "average_turns",
        "invalid_action_rate",
    )
    for metric in metrics:
        base_value = baseline_summary[metric]
        candidate_value = candidate_summary[metric]
        delta = round(candidate_value - base_value, 4)
        print(
            f"{metric:<20} baseline={base_value:.4f} "
            f"candidate={candidate_value:.4f} delta={delta:+.4f}"
        )


def _write_json(output_path: str, payload: dict[str, Any]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _aggregate_summaries(model: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not summaries:
        return {
            "model": model,
            "runs": 0,
            "mean_average_score": 0.0,
            "mean_success_rate": 0.0,
            "mean_average_turns": 0.0,
            "mean_invalid_action_rate": 0.0,
            "task_score_means": {},
        }

    task_ids = sorted(
        {task_id for summary in summaries for task_id in summary.get("task_scores", {})}
    )
    task_score_means = {
        task_id: round(
            sum(summary["task_scores"].get(task_id, 0.0) for summary in summaries)
            / len(summaries),
            4,
        )
        for task_id in task_ids
    }
    return {
        "model": model,
        "runs": len(summaries),
        "mean_average_score": round(
            sum(summary["average_score"] for summary in summaries) / len(summaries), 4
        ),
        "mean_success_rate": round(
            sum(summary["success_rate"] for summary in summaries) / len(summaries), 4
        ),
        "mean_average_turns": round(
            sum(summary["average_turns"] for summary in summaries) / len(summaries), 4
        ),
        "mean_invalid_action_rate": round(
            sum(summary["invalid_action_rate"] for summary in summaries) / len(summaries), 4
        ),
        "task_score_means": task_score_means,
    }


def _comparison_delta(
    baseline_aggregate: dict[str, Any], candidate_aggregate: dict[str, Any]
) -> dict[str, float]:
    metrics = (
        "mean_average_score",
        "mean_success_rate",
        "mean_average_turns",
        "mean_invalid_action_rate",
    )
    return {
        metric: round(candidate_aggregate[metric] - baseline_aggregate[metric], 4)
        for metric in metrics
    }


def _save_run_artifacts(
    output_dir: str,
    role: str,
    run_index: int,
    summary: dict[str, Any],
    episodes: list[EpisodeStats],
) -> None:
    payload = {
        "recorded_at": _timestamp(),
        "role": role,
        "run_index": run_index,
        "summary": summary,
        "episodes": [episode.to_dict() for episode in episodes],
    }
    _write_json(
        str(Path(output_dir) / f"{role}_run_{run_index:03d}.json"),
        payload,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Primary Ollama model, e.g. codellama:7b")
    parser.add_argument(
        "--compare-model",
        help="Optional second model to compare against, e.g. finetuned-codellama:latest",
    )
    parser.add_argument("--domain", default="saas", choices=["saas"])
    parser.add_argument("--base-url", default=DEFAULT_ENV_URL)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--output-json",
        help="Optional path to write JSON results for plotting/reporting.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for per-run JSON artifacts and aggregate summaries.",
    )
    args = parser.parse_args()

    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")

    primary_runs: list[dict[str, Any]] = []
    for run_index in range(1, args.repeats + 1):
        print(f"\n=== Primary model run {run_index}/{args.repeats} ===")
        summary, episodes = run_model_suite(
            model=args.model,
            domain_name=args.domain,
            base_url=args.base_url,
            max_turns=args.max_turns,
        )
        _print_summary(summary)
        primary_runs.append(summary)
        if args.output_dir:
            _save_run_artifacts(args.output_dir, "primary", run_index, summary, episodes)

    primary_aggregate = _aggregate_summaries(args.model, primary_runs)
    payload: dict[str, Any] = {
        "recorded_at": _timestamp(),
        "primary": {
            "runs": primary_runs,
            "aggregate": primary_aggregate,
        }
    }

    print("")
    print(f"Primary Aggregate ({args.model})")
    print(json.dumps(primary_aggregate, indent=2))

    if args.compare_model:
        comparison_runs: list[dict[str, Any]] = []
        for run_index in range(1, args.repeats + 1):
            print(f"\n=== Comparison model run {run_index}/{args.repeats} ===")
            summary, episodes = run_model_suite(
                model=args.compare_model,
                domain_name=args.domain,
                base_url=args.base_url,
                max_turns=args.max_turns,
            )
            _print_summary(summary)
            comparison_runs.append(summary)
            if args.output_dir:
                _save_run_artifacts(
                    args.output_dir, "comparison", run_index, summary, episodes
                )

        comparison_aggregate = _aggregate_summaries(args.compare_model, comparison_runs)
        _print_comparison(primary_aggregate, comparison_aggregate)
        payload["comparison"] = {
            "runs": comparison_runs,
            "aggregate": comparison_aggregate,
        }
        payload["delta"] = _comparison_delta(primary_aggregate, comparison_aggregate)

        print("")
        print(f"Comparison Aggregate ({args.compare_model})")
        print(json.dumps(comparison_aggregate, indent=2))

    if args.output_json:
        _write_json(args.output_json, payload)
    if args.output_dir:
        _write_json(str(Path(args.output_dir) / "summary.json"), payload)


if __name__ == "__main__":
    main()
