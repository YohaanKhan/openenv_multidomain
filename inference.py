"""
Competition inference script for openenv_multidomain.
Required env vars:
  - OPENAI_API_KEY   : your OpenAI or compatible API key
  - API_BASE_URL     : the API endpoint for the LLM (default: https://api.openai.com/v1)
  - MODEL_NAME       : the model identifier (default: gpt-4o-mini)
  - HF_TOKEN         : Hugging Face token (used to authenticate with HF Space)
  - HF_SPACE_URL     : base URL of the deployed HF Space (default: http://localhost:7860)
  - DOMAIN           : which domain to run (saas | hr | legal), default: saas
"""

from __future__ import annotations

import json
import os
import time
import sys
from typing import Any

from openai import OpenAI

# --------------------------------------------------------------------------- #
# Env var wiring (competition-required names)
# --------------------------------------------------------------------------- #
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN", "")  # validated but not used in HTTP calls directly
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", HF_TOKEN)  # fall back to HF_TOKEN if set
HF_SPACE_URL = os.getenv("HF_SPACE_URL", "http://localhost:7860")
DOMAIN = os.getenv("DOMAIN", "saas")
ENV_RETRY_ATTEMPTS = int(os.getenv("ENV_RETRY_ATTEMPTS", "3"))
ENV_RETRY_BACKOFF_S = float(os.getenv("ENV_RETRY_BACKOFF_S", "2"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.01"))
MAX_SCORE = float(os.getenv("MAX_SCORE", "0.99"))


# --------------------------------------------------------------------------- #
# Local imports (works both as top-level script and as a module)
# --------------------------------------------------------------------------- #
try:
    import domains  # noqa: F401  — registers all domain plugins
    from client import MultiDomainEnv
    from models import EnvAction
    from server.domain_registry import DomainRegistry
except ImportError:
    from . import domains  # noqa: F401
    from .client import MultiDomainEnv
    from .models import EnvAction
    from .server.domain_registry import DomainRegistry


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _escape_structured_value(value: Any) -> str:
    """Render a single-line value for structured stdout."""
    text = str(value)
    return text.replace("\n", "\\n").replace("\r", "\\r")


def _normalize_score(score: float) -> float:
    """Clamp scores into the validator-required open interval (0, 1)."""
    if MIN_SCORE >= MAX_SCORE:
        raise ValueError("MIN_SCORE must be less than MAX_SCORE.")
    return min(max(float(score), MIN_SCORE), MAX_SCORE)


def _print_structured_start(task_id: str, env_name: str, model_name: str) -> None:
    """Emit validator-friendly task start output."""
    print(
        f"[START] task={_escape_structured_value(task_id)} "
        f"env={_escape_structured_value(env_name)} "
        f"model={_escape_structured_value(model_name)}",
        flush=True,
    )


def _print_structured_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: str | None,
) -> None:
    """Emit validator-friendly per-step output."""
    error_value = _escape_structured_value(error) if error else "null"
    print(
        f"[STEP] step={step} "
        f"action={_escape_structured_value(action)} "
        f"reward={reward:.2f} "
        f"done={str(done).lower()} "
        f"error={error_value}",
        flush=True,
    )


def _print_structured_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    """Emit validator-friendly task completion output."""
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} "
        f"steps={steps} "
        f"score={score:.2f} "
        f"rewards={rewards_str}",
        flush=True,
    )


def _extract_text(response: Any) -> str:
    """Extract text content from OpenAI Chat Completions response."""
    choice = response.choices[0].message
    content = choice.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
        if parts:
            return "".join(parts)
    raise ValueError("OpenAI response contained no text content.")


def _request_agent_action(client: OpenAI, messages: list[dict[str, Any]]) -> str:
    """
    Request the next JSON action from the model with a compatibility fallback.

    Some OpenAI-compatible endpoints reject JSON mode even though the rest of the
    chat completions API works. We retry once without `response_format` so the
    script degrades gracefully instead of crashing the whole validation run.
    """
    request_kwargs = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 400,
    }

    try:
        response = client.chat.completions.create(
            response_format={"type": "json_object"},
            **request_kwargs,
        )
        return _extract_text(response)
    except Exception as exc:
        print(
            "  [llm] JSON-mode request failed; retrying without response_format. "
            f"{type(exc).__name__}: {exc}"
        )

    response = client.chat.completions.create(**request_kwargs)
    return _extract_text(response)


def _reset_for_task(env: Any, task_id: str, total_tasks: int) -> Any:
    """
    Reset to a specific task_id.
    First tries passing task_id as a kwarg; if not supported,
    cycles through resets deterministically until the right task appears.
    Raises RuntimeError if it cannot align after total_tasks attempts.
    """
    # Attempt direct task_id kwarg first
    try:
        result = env.reset(task_id=task_id)
        if result.observation.info.get("task_id") == task_id:
            return result
    except Exception:
        pass

    # Fallback: cycle through rotation
    for attempt in range(total_tasks + 1):
        result = env.reset()
        observed = result.observation.info.get("task_id")
        if observed == task_id:
            return result
        if attempt == total_tasks:
            raise RuntimeError(
                f"Could not align reset() to task '{task_id}' after {total_tasks + 1} attempts. "
                f"Last observed task: '{observed}'. "
                "Fix: ensure the server accepts task_id in reset() body."
            )
    return result  # unreachable but satisfies type checkers


def build_system_prompt(domain_name: str, task: dict) -> str:
    """Build system prompt for the LLM agent."""
    return f"""You are an expert {domain_name} agent. Your goal is to complete the following task:

Task ID: {task['id']}
Difficulty: {task['difficulty']}
Objective: {task.get('objective', 'See initial observation.')}

You interact with the environment by calling tools. At each step you MUST respond with a JSON object:
{{
  "tool_name": "<name of the tool to call>",
  "tool_args": {{ "<arg_name>": "<arg_value>" }},
  "thought": "<your reasoning before calling this tool>"
}}

Rules:
- Do NOT repeat the same tool call with the same args consecutively.
- Do NOT call a tool unless you have a clear reason to do so.
- When the task is complete, call the `done` tool (or whichever finalization tool exists for this domain).
- Respond ONLY with the JSON object — no extra text, no markdown fences.
"""


def run_episode(
    env: Any,
    client: OpenAI,
    task: dict,
    domain_name: str,
    max_turns: int = 30,
) -> tuple[float, int, list[float], bool]:
    """Run one episode for a single task. Returns score, steps, rewards, success."""
    task_id = task["id"]
    total_tasks = int(os.getenv("DOMAIN_TASK_COUNT", "3"))

    initial = _reset_for_task(env, task_id, total_tasks)
    observation = initial.observation
    done = initial.done

    system_prompt = build_system_prompt(domain_name, task)
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": observation.content},
    ]

    turns = 0
    last_tool_call = None
    consecutive_repeats = 0
    rewards: list[float] = []

    while not done and turns < max_turns:
        turns += 1

        try:
            raw = _request_agent_action(client, messages)
        except Exception as exc:
            print(
                f"  [turn {turns}] LLM request failed; ending task early. "
                f"{type(exc).__name__}: {exc}"
            )
            break

        try:
            action_dict = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  [turn {turns}] JSON parse error — skipping turn. Raw: {raw[:80]}")
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "ERROR: your response was not valid JSON. Try again with a valid JSON object.",
                }
            )
            continue

        tool_name = action_dict.get("tool_name", "")
        tool_args = action_dict.get("tool_args", {})
        thought = action_dict.get("thought", "")
        action_str = json.dumps(
            {
                "tool_name": tool_name,
                "tool_args": tool_args,
                "thought": thought,
            },
            sort_keys=True,
        )

        # Detect infinite loop / repeated identical calls
        current_call = (tool_name, json.dumps(tool_args, sort_keys=True))
        if current_call == last_tool_call:
            consecutive_repeats += 1
            if consecutive_repeats >= 3:
                print(f"  [turn {turns}] WARNING: same tool call repeated 3x — forcing episode end.")
                break
        else:
            consecutive_repeats = 0
        last_tool_call = current_call

        action = EnvAction(tool_name=tool_name, tool_args=tool_args, thought=thought)
        try:
            step_result = env.step(action)
        except Exception as exc:
            print(
                f"  [turn {turns}] Environment step failed; ending task early. "
                f"{type(exc).__name__}: {exc}"
            )
            _print_structured_step(turns, action_str, 0.0, False, str(exc))
            break
        observation = step_result.observation
        done = step_result.done
        reward = float(step_result.reward or 0.0)
        rewards.append(reward)

        print(f"  [turn {turns}] tool={tool_name} | reward={reward:.4f} | done={done}")
        _print_structured_step(turns, action_str, reward, bool(done), None)

        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": observation.content})

    grader_score = _normalize_score(float(observation.info.get("grader_score") or 0.0))
    success = done and grader_score > MIN_SCORE
    return grader_score, turns, rewards, success


def run_all_tasks(domain_name: str) -> dict[str, float]:
    """Run one episode per task in the domain. Returns {task_id: score}."""
    if not OPENAI_API_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY (or HF_TOKEN) before running inference.py")

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=API_BASE_URL)
    domain = DomainRegistry.require(domain_name)()
    tasks = domain.get_tasks()

    scores: dict[str, float] = {}
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Domain: {domain_name} | Task: {task['id']} ({task.get('difficulty','?')})")
        print(f"{'='*60}")
        _print_structured_start(task["id"], domain_name, MODEL_NAME)

        score = MIN_SCORE
        steps = 0
        rewards: list[float] = []
        success = False
        for attempt in range(1, ENV_RETRY_ATTEMPTS + 1):
            env = MultiDomainEnv(base_url=HF_SPACE_URL).sync()
            try:
                if attempt > 1:
                    print(f"  [env] retry attempt {attempt}/{ENV_RETRY_ATTEMPTS}")
                score, steps, rewards, success = run_episode(env, client, task, domain_name)
                break
            except Exception as exc:
                print(
                    f"  [env] task attempt {attempt} failed. "
                    f"{type(exc).__name__}: {exc}"
                )
                if attempt == ENV_RETRY_ATTEMPTS:
                    print("  => Exhausted environment retries; recording 0.0.")
                else:
                    sleep_s = ENV_RETRY_BACKOFF_S * attempt
                    print(f"  [env] waiting {sleep_s:.1f}s before reconnecting...")
                    time.sleep(sleep_s)
            finally:
                env.close()

        scores[task["id"]] = round(_normalize_score(score), 4)
        _print_structured_end(success, steps, scores[task["id"]], rewards)
        print(f"  => Final grader score: {scores[task['id']]:.4f}")

    return scores


def print_results(domain_name: str, scores: dict[str, float]) -> None:
    """Print a summary of scores."""
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"\n{'='*60}")
    print(f"RESULTS — domain: {domain_name}  model: {MODEL_NAME}")
    print(f"{'='*60}")
    for task_id, score in scores.items():
        print(f"  {task_id:<25} {score:.4f}")
    print(f"  {'AVERAGE':<25} {avg:.4f}")
    print(f"{'='*60}\n")


def main() -> None:
    """Main entry point."""
    try:
        scores = run_all_tasks(DOMAIN)
    except EnvironmentError as exc:
        sys.exit(f"ERROR: {exc}")
    print_results(DOMAIN, scores)


if __name__ == "__main__":
    main()
