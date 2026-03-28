"""Multidomain OpenEnv environment that drives domain plugins without importing them."""

from __future__ import annotations

import os
import time
from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from pydantic import ValidationError

try:
    from ..models import EnvAction, EnvObservation
except ImportError:
    from models import EnvAction, EnvObservation
from .domain_registry import DomainRegistry
from .system_prompt_builder import SystemPromptBuilder
from .utils.db import TransactionManager, engine
from .utils.logger import get_logger, trace_id_var
from .utils.metrics import (
    episodes_total,
    episode_duration,
    grader_scores,
    steps_total,
    tool_errors_total,
)


logger = get_logger(__name__)


class MultiDomainEnvironment(Environment):
    """Core engine that orchestrates domain plugins via BaseDomain/graders."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._domain_name = os.environ.get("DOMAIN", "saas")
        domain_cls = DomainRegistry.require(self._domain_name)
        self._domain = domain_cls()
        self._domain.create_tables(engine)
        self._tools = self._domain.get_tools()
        self._tasks = self._domain.get_tasks()
        self._system_prompt = SystemPromptBuilder.build(
            self._domain.get_system_prompt_template(), self._tools
        )

        self._tx = TransactionManager()
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._trajectory: list[dict[str, Any]] = []
        self._task: dict[str, Any] | None = None
        self._episode_start_time: float | None = None
        self._task_counter = 0

    def reset(self, task_id: str | None = None) -> EnvObservation:
        """Reset the environment, seed the next task, and start a new savepoint.
        
        Args:
            task_id: Optional task ID to reset to. If not provided, rotates through tasks.
                    
        Raises:
            ValueError: If task_id is provided but not found in available tasks.
        """
        self._tx.rollback_episode()
        episode_id = str(uuid4())
        self._state = State(episode_id=episode_id, step_count=0)
        self._trajectory = []
        self._episode_start_time = time.time()
        trace_id_var.set(episode_id)

        self._tx.begin_episode()
        session = self._tx.get_session()

        if not self._tasks:
            raise RuntimeError("No tasks registered for the domain.")

        # Select task based on task_id if provided, otherwise rotate
        if task_id is not None:
            matched = next((t for t in self._tasks if t["id"] == task_id), None)
            if matched is None:
                available_ids = [t["id"] for t in self._tasks]
                raise ValueError(
                    f"Unknown task_id '{task_id}'. Available: {available_ids}"
                )
            self._task = matched
        else:
            task_idx = self._task_counter % len(self._tasks)
            self._task = self._tasks[task_idx]
            self._task_counter += 1

        seed_payload = self._domain.seed_episode(self._task["id"], session)
        task_description = seed_payload.get("description", self._task.get("description", ""))

        episodes_total.labels(
            domain=self._domain_name, task_id=self._task["id"], status="started"
        ).inc()

        info = self._build_info(step_count=0, done=False, grader_score=None, step_limit_hit=False)
        observation = EnvObservation(
            content=f"{self._system_prompt}\n\n---\nTask: {task_description}",
            done=False,
            reward=0.0,
            info=info,
        )
        return observation

    def step(self, action: EnvAction) -> EnvObservation:
        """Run a tool action, compute reward, and trigger graders when done."""
        if self._task is None:
            raise RuntimeError("reset() must be called before step().")

        self._state.step_count += 1
        session = self._tx.get_session()
        max_steps = self._task.get("max_steps", 20)

        steps_total.labels(domain=self._domain_name, tool_name=action.tool_name).inc()

        tool_args_dump: dict = action.tool_args
        result = ""
        reward = 0.0
        error: str | None = None
        domain_done = False

        if action.tool_name not in self._tools:
            result = (
                f"Error: '{action.tool_name}' is not a valid tool. "
                f"Available: {sorted(self._tools.keys())}"
            )
            reward = -0.05
            error = result
            tool_errors_total.labels(
                domain=self._domain_name, tool_name=action.tool_name, error_type="invalid_tool"
            ).inc()
        else:
            tool = self._tools[action.tool_name]
            try:
                validated_args = tool["schema"](**action.tool_args)
            except (ValidationError, TypeError) as exc:
                result = f"Error validating args for '{action.tool_name}': {exc}"
                reward = -0.10
                error = result
                tool_errors_total.labels(
                    domain=self._domain_name,
                    tool_name=action.tool_name,
                    error_type="bad_args",
                ).inc()
            else:
                tool_args_dump = validated_args.model_dump()
                try:
                    raw_result = tool["func"](validated_args, session)
                    result = str(raw_result)
                    reward = self._domain.compute_step_reward(
                        action.tool_name, result, session, self._state.step_count
                    )
                    domain_done = self._domain.is_done(action.tool_name, result, session)
                except Exception as exc:
                    logger.exception("Runtime error while executing tool %s", action.tool_name)
                    result = f"Runtime error while executing '{action.tool_name}': {exc}"
                    reward = -0.10
                    error = result
                    tool_errors_total.labels(
                        domain=self._domain_name,
                        tool_name=action.tool_name,
                        error_type="runtime",
                    ).inc()

        step_limit_hit = self._state.step_count >= max_steps
        done = domain_done or step_limit_hit

        self._record_step(
            tool_name=action.tool_name,
            tool_args=tool_args_dump,
            thought=action.thought,
            result=result,
            reward=reward,
        )

        grader_score: float | None = None
        if done:
            grader_score = self._run_graders(session)

            if self._episode_start_time is not None:
                duration = time.time() - self._episode_start_time
            else:
                duration = 0.0

            episode_duration.labels(domain=self._domain_name).observe(duration)
            grader_scores.labels(
                domain=self._domain_name,
                task_id=self._task["id"],
                difficulty=self._task.get("difficulty", "unknown"),
            ).observe(grader_score if grader_score is not None else 0.0)

            status = (
                "completed" if domain_done else "timeout" if step_limit_hit else "error"
            )
            episodes_total.labels(
                domain=self._domain_name, task_id=self._task["id"], status=status
            ).inc()

            self._tx.rollback_episode()
            self._episode_start_time = None

        info = self._build_info(
            step_count=self._state.step_count,
            done=done,
            grader_score=grader_score,
            step_limit_hit=step_limit_hit,
            error=error,
        )

        return EnvObservation(content=result, done=done, reward=reward, info=info)

    @property
    def state(self) -> State:
        """Current episode state exposed to OpenEnv clients."""
        return self._state

    def _run_graders(self, session: Any) -> float:
        """Run all domain graders deterministically and return an average score."""
        graders = self._domain.get_graders()
        if not graders:
            return 0.0

        scores: list[float] = []
        for grader in graders:
            try:
                result = grader.grade(self._trajectory, session)
                scores.append(float(result.get("score", 0.0)))
            except Exception:
                logger.exception("Grader %s failed", grader.__class__.__name__)
                scores.append(0.0)
        return sum(scores) / len(scores)

    def _record_step(
        self,
        tool_name: str,
        tool_args: dict,
        thought: str,
        result: str,
        reward: float,
    ) -> None:
        """Append step data for graders and auditing."""
        self._trajectory.append(
            {
                "step_idx": self._state.step_count,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "thought": thought,
                "result": result,
                "reward": reward,
            }
        )

    def _build_info(
        self,
        step_count: int,
        done: bool,
        grader_score: float | None,
        step_limit_hit: bool,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Consistent metadata included in every observation."""
        info = {
            "step_count": step_count,
            "task_id": self._task["id"] if self._task else None,
            "task_difficulty": self._task.get("difficulty") if self._task else None,
            "trace_id": trace_id_var.get(),
            "domain": self._domain_name,
        }
        if error:
            info["error"] = error
        if done:
            info["grader_score"] = grader_score
            info["step_limit_hit"] = step_limit_hit
        return info
