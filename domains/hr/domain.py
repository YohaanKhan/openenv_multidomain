"\"\"\"HR domain wiring to BaseDomain.\"\"\""

from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from domains.hr import schema  # noqa: F401
from domains.hr.graders.code_grader import HRCodeGrader
from domains.hr.graders.llm_grader import HRLLMGrader
from domains.hr.prompts import SYSTEM_PROMPT_TEMPLATE
from domains.hr.tasks import TASKS, seed as seed_task
from domains.hr.tools import definitions as defs
from domains.hr.tools import implementation as impl
from server.interfaces import BaseDomain, BaseGrader
from server.utils.db import Base


class HRDomain(BaseDomain):
    """HR domain implementation."""

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
            "lookup_policy": {"schema": defs.LookupPolicyArgs, "func": impl.lookup_policy},
            "get_employee_record": {
                "schema": defs.GetEmployeeRecordArgs,
                "func": impl.get_employee_record,
            },
            "check_leave_balance": {
                "schema": defs.CheckLeaveBalanceArgs,
                "func": impl.check_leave_balance,
            },
            "file_leave_request": {
                "schema": defs.FileLeaveRequestArgs,
                "func": impl.file_leave_request,
            },
            "get_benefits_summary": {
                "schema": defs.GetBenefitsSummaryArgs,
                "func": impl.get_benefits_summary,
            },
            "send_hr_notification": {
                "schema": defs.SendHRNotificationArgs,
                "func": impl.send_hr_notification,
            },
            "close_hr_request": {
                "schema": defs.CloseHRRequestArgs,
                "func": impl.close_hr_request,
            },
        }

    def get_tasks(self) -> list[dict]:
        return TASKS

    def compute_step_reward(
        self, tool_name: str, tool_result: str, session: Session, step_count: int
    ) -> float:
        result_lower = tool_result.lower()
        if (
            "not found" in result_lower
            or "error" in result_lower
            or "insufficient" in result_lower
        ):
            return -0.05
        if tool_name == "close_hr_request" and "closed" in result_lower:
            return 0.40
        if tool_name == "file_leave_request" and "reference number" in result_lower:
            return 0.25
        if tool_name == "send_hr_notification":
            return 0.10
        if tool_name in (
            "lookup_policy",
            "get_employee_record",
            "check_leave_balance",
            "get_benefits_summary",
        ):
            return 0.05
        return 0.0

    def is_done(self, tool_name: str, tool_result: str, session: Session) -> bool:
        return tool_name == "close_hr_request" and "closed" in tool_result.lower()

    def get_graders(self) -> list[BaseGrader]:
        return [HRCodeGrader(), HRLLMGrader()]

    def get_system_prompt_template(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE
