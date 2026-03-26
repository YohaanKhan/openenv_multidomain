"""SaaS domain implementation wiring the schema, tools, tasks, and graders."""

from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from domains.saas import schema  # noqa: F401
from domains.saas.graders.code_grader import SaaSCodeGrader
from domains.saas.graders.llm_grader import SaaSLLMGrader
from domains.saas.prompts import SYSTEM_PROMPT_TEMPLATE
from domains.saas.tasks import TASKS, seed as seed_task
from domains.saas.tools import definitions as defs
from domains.saas.tools import implementation as impl
from server.interfaces import BaseDomain, BaseGrader
from server.utils.db import Base


class SaaSDomain(BaseDomain):
    """Adapter that exposes the SaaS domain through BaseDomain contract."""

    def create_tables(self, engine) -> None:
        try:
            Base.metadata.create_all(engine)
        except OperationalError as exc:
            if "already exists" not in str(exc).lower():
                raise

    def seed_episode(self, task_id: str, session: Session) -> dict:
        return seed_task(task_id, session)

    def get_tools(self) -> dict[str, dict]:
        return {
            "search_tickets": {"schema": defs.SearchTicketsArgs, "func": impl.search_tickets},
            "get_account": {"schema": defs.GetAccountArgs, "func": impl.get_account},
            "get_transactions": {
                "schema": defs.GetTransactionsArgs,
                "func": impl.get_transactions,
            },
            "issue_refund": {"schema": defs.IssueRefundArgs, "func": impl.issue_refund},
            "send_email": {"schema": defs.SendEmailArgs, "func": impl.send_email},
            "escalate_ticket": {
                "schema": defs.EscalateTicketArgs,
                "func": impl.escalate_ticket,
            },
            "close_ticket": {"schema": defs.CloseTicketArgs, "func": impl.close_ticket},
        }

    def get_tasks(self) -> list[dict]:
        return TASKS

    def compute_step_reward(
        self, tool_name: str, tool_result: str, session: Session, step_count: int
    ) -> float:
        result_lower = tool_result.lower()
        if (
            "not found" in result_lower
            or result_lower.startswith("no ")
            or "no tickets found" in result_lower
            or "no customer found" in result_lower
            or "no transactions found" in result_lower
            or result_lower.startswith("error:")
            or result_lower.startswith("runtime error")
        ):
            return -0.05
        if (
            "does not belong" in result_lower
            or "already been refunded" in result_lower
            or "exceeds original charge" in result_lower
        ):
            return -0.10
        if tool_name == "close_ticket" and "closed" in result_lower:
            return 0.40
        if tool_name == "issue_refund" and "refund issued" in result_lower:
            return 0.30
        if tool_name == "escalate_ticket" and "escalated" in result_lower:
            return 0.25
        if tool_name == "send_email" and "sent" in result_lower:
            return 0.10
        if tool_name in ("search_tickets", "get_account"):
            return 0.05
        if tool_name == "get_transactions":
            return 0.08
        return 0.0

    def is_done(self, tool_name: str, tool_result: str, session: Session) -> bool:
        return tool_name == "close_ticket" and "closed" in tool_result.lower()

    def get_graders(self) -> list[BaseGrader]:
        return [SaaSCodeGrader(), SaaSLLMGrader()]

    def get_system_prompt_template(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE
