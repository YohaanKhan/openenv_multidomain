from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from sqlalchemy.orm import Session


class BaseDomain(ABC):
    """Contract every domain plugin must satisfy before the engine can drive it."""

    @abstractmethod
    def create_tables(self, engine) -> None:
        """
        Create domain-specific SQLAlchemy tables using the provided engine.

        This is invoked once during startup so the domain can define its own schema.
        """

    @abstractmethod
    def seed_episode(self, task_id: str, session: Session) -> dict:
        """
        Seed the database for the requested task and return descriptive metadata.

        Returns a dictionary with at least {"description": str} that the engine shows
        to the agent so it understands the task prompt.
        """

    @abstractmethod
    def get_tools(self) -> dict[str, dict]:
        """
        Return the tool registry for this domain.

        Each entry should map tool names to a dict containing "schema" (the Pydantic
        schema class the LLM sees) and "func" (a callable that executes the tool).
        """

    @abstractmethod
    def get_tasks(self) -> list[dict]:
        """
        Describe the domain's available tasks.

        The engine expects exactly three tasks (easy, medium, hard), each of which
        must include id, name, difficulty, description, and max_steps keys.
        """

    @abstractmethod
    def compute_step_reward(
        self, tool_name: str, tool_result: str, session: Session, step_count: int
    ) -> float:
        """
        Shape rewards per tool execution.

        Should return a float in [-0.5, 1.0]. The engine already applies penalties for
        invalid tools (-0.05) and bad args (-0.10) so this method focuses on domain
        semantics and progress toward completion.
        """

    @abstractmethod
    def is_done(self, tool_name: str, tool_result: str, session: Session) -> bool:
        """
        Determine whether the current episode should end after the given tool run.

        The engine will also terminate when a task's max_steps is reached.
        """

    @abstractmethod
    def get_graders(self) -> list[BaseGrader]:
        """
        Return the graders that should evaluate final trajectories for this domain.

        Graders run only after an episode terminates and must be deterministic.
        """

    @abstractmethod
    def get_system_prompt_template(self) -> str:
        """
        Provide the system prompt template that consumes `{tool_docs}`.

        The prompt builder renders the template with the tool documentation gathered
        from the domain's schemas.
        """


class BaseGrader(ABC):
    """Deterministic grader interface for evaluating completed trajectories."""

    @abstractmethod
    def grade(self, trajectory: list[dict], session: Session | None) -> dict:
        """
        Score the episode's trajectory while optionally using a DB session.

        Must return {"score": float, "success": bool, "feedback": str}. The grader
        needs to behave deterministically and handle session=None for /grader calls.
        """
