"""Run Hugging Face Transformer models against the SaaS benchmark domain."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import domains  # noqa: F401
from benchmarks.run_saas_ollama import (
    DEFAULT_ENV_URL,
    EpisodeStats,
    _aggregate_summaries,
    _comparison_delta,
    _coerce_action_dict,
    _print_comparison,
    _print_summary,
    _reset_for_task,
    _save_run_artifacts,
    _summarize_runs,
    _timestamp,
    _write_json,
)
from client import MultiDomainEnv
from models import EnvAction
from server.domain_registry import DomainRegistry


DEFAULT_SYSTEM_PROMPT = (
    "Reply with a single JSON object only. "
    'Use exactly: {"tool_name": str, "tool_args": object, "thought": str}. '
    "Use concrete IDs returned by prior tool outputs. Do not invent IDs."
)


@dataclass
class LoadedModel:
    label: str
    tokenizer: Any
    model: Any


def _resolve_model_label(model_name: str, adapter_path: str | None) -> str:
    if adapter_path:
        return Path(adapter_path).name
    return model_name


def _resolve_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_transformer_model(model_name: str, adapter_path: str | None) -> LoadedModel:
    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Training/inference dependencies are missing. Install the train extras first, "
            "for example: `./../venv/bin/python -m pip install -e '.[train]'`."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = _resolve_device()
    model_kwargs: dict[str, Any] = {}
    if device != "cpu":
        model_kwargs["torch_dtype"] = torch.float16

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    if adapter_path:
        model = PeftModel.from_pretrained(model, adapter_path)
    model.to(device)
    model.eval()

    return LoadedModel(
        label=_resolve_model_label(model_name, adapter_path),
        tokenizer=tokenizer,
        model=model,
    )


def _render_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    parts = []
    for message in messages:
        parts.append(f"{message['role'].upper()}:\n{message['content']}")
    parts.append("ASSISTANT:")
    return "\n\n".join(parts)


def _generate_model_reply(loaded: LoadedModel, messages: list[dict[str, str]], max_new_tokens: int) -> str:
    prompt = _render_prompt(loaded.tokenizer, messages)
    encoded = loaded.tokenizer(prompt, return_tensors="pt")
    device = next(loaded.model.parameters()).device
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.inference_mode():
        generated = loaded.model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            pad_token_id=loaded.tokenizer.pad_token_id,
            eos_token_id=loaded.tokenizer.eos_token_id,
        )

    prompt_length = encoded["input_ids"].shape[-1]
    completion = generated[0][prompt_length:]
    return loaded.tokenizer.decode(completion, skip_special_tokens=True).strip()


def run_episode(
    env: Any,
    loaded: LoadedModel,
    task_id: str,
    max_turns: int = 30,
    max_new_tokens: int = 300,
) -> EpisodeStats:
    try:
        initial = _reset_for_task(env, task_id, known_task_count=3)
        observation = initial.observation
        done = initial.done
        turns = 0
        invalid_actions = 0

        messages: list[dict[str, str]] = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": observation.content},
        ]

        while not done and turns < max_turns:
            turns += 1
            raw = _generate_model_reply(
                loaded=loaded,
                messages=messages,
                max_new_tokens=max_new_tokens,
            )
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
                f"[{loaded.label}] [turn {turns}] task={task_id} tool={action.tool_name} "
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
        print(f"[{loaded.label}] task={task_id} failed: {exc}")
        return EpisodeStats(
            task_id=task_id,
            score=0.0,
            turns=0,
            invalid_actions=1,
            total_actions=1,
            error=str(exc),
        )


def run_model_suite(
    model_name: str,
    adapter_path: str | None,
    domain_name: str = "saas",
    base_url: str = DEFAULT_ENV_URL,
    max_turns: int = 30,
    max_new_tokens: int = 300,
) -> tuple[dict[str, Any], list[EpisodeStats]]:
    domain = DomainRegistry.require(domain_name)()
    tasks = domain.get_tasks()
    loaded = _load_transformer_model(model_name=model_name, adapter_path=adapter_path)

    episodes: list[EpisodeStats] = []
    with MultiDomainEnv(base_url=base_url).sync() as env:
        for task in tasks:
            print(f"Running [{loaded.label}] task: {task['id']} ({task['difficulty']})")
            episodes.append(
                run_episode(
                    env=env,
                    loaded=loaded,
                    task_id=task["id"],
                    max_turns=max_turns,
                    max_new_tokens=max_new_tokens,
                )
            )

    return _summarize_runs(loaded.label, episodes), episodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Base Hugging Face model id or local path.")
    parser.add_argument(
        "--adapter-path",
        help="Optional LoRA adapter directory to load on top of --model.",
    )
    parser.add_argument(
        "--compare-model",
        help="Optional second base model id or local path.",
    )
    parser.add_argument(
        "--compare-adapter-path",
        help="Optional LoRA adapter directory for --compare-model.",
    )
    parser.add_argument("--domain", default="saas", choices=["saas"])
    parser.add_argument("--base-url", default=DEFAULT_ENV_URL)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=300)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output-json")
    parser.add_argument("--output-dir")
    args = parser.parse_args()

    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")

    primary_runs: list[dict[str, Any]] = []
    primary_role = "primary"
    for run_index in range(1, args.repeats + 1):
        print(f"\n=== Primary model run {run_index}/{args.repeats} ===")
        summary, episodes = run_model_suite(
            model_name=args.model,
            adapter_path=args.adapter_path,
            domain_name=args.domain,
            base_url=args.base_url,
            max_turns=args.max_turns,
            max_new_tokens=args.max_new_tokens,
        )
        _print_summary(summary)
        primary_runs.append(summary)
        if args.output_dir:
            _save_run_artifacts(args.output_dir, primary_role, run_index, summary, episodes)

    primary_label = _resolve_model_label(args.model, args.adapter_path)
    primary_aggregate = _aggregate_summaries(primary_label, primary_runs)
    payload: dict[str, Any] = {
        "recorded_at": _timestamp(),
        "primary": {"runs": primary_runs, "aggregate": primary_aggregate},
    }

    print("")
    print(f"Primary Aggregate ({primary_label})")
    print(json.dumps(primary_aggregate, indent=2))

    if args.compare_model:
        comparison_runs: list[dict[str, Any]] = []
        for run_index in range(1, args.repeats + 1):
            print(f"\n=== Comparison model run {run_index}/{args.repeats} ===")
            summary, episodes = run_model_suite(
                model_name=args.compare_model,
                adapter_path=args.compare_adapter_path,
                domain_name=args.domain,
                base_url=args.base_url,
                max_turns=args.max_turns,
                max_new_tokens=args.max_new_tokens,
            )
            _print_summary(summary)
            comparison_runs.append(summary)
            if args.output_dir:
                _save_run_artifacts(args.output_dir, "comparison", run_index, summary, episodes)

        comparison_label = _resolve_model_label(args.compare_model, args.compare_adapter_path)
        comparison_aggregate = _aggregate_summaries(comparison_label, comparison_runs)
        _print_comparison(primary_aggregate, comparison_aggregate)
        payload["comparison"] = {
            "runs": comparison_runs,
            "aggregate": comparison_aggregate,
        }
        payload["delta"] = _comparison_delta(primary_aggregate, comparison_aggregate)

        print("")
        print(f"Comparison Aggregate ({comparison_label})")
        print(json.dumps(comparison_aggregate, indent=2))

    if args.output_json:
        _write_json(args.output_json, payload)
    if args.output_dir:
        _write_json(str(Path(args.output_dir) / "summary.json"), payload)


if __name__ == "__main__":
    main()
