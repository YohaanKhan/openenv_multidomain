"""Legal domain adapter."""

from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from domains.legal import schema  # noqa: F401
from domains.legal.graders.code_grader import LegalCodeGrader
from domains.legal.graders.llm_grader import LegalLLMGrader
from domains.legal.prompts import SYSTEM_PROMPT_TEMPLATE
from domains.legal.tasks import TASKS, seed as seed_task
from domains.legal.tools import definitions as defs
from domains.legal.tools import implementation as impl
from server.interfaces import BaseDomain, BaseGrader
from server.utils.db import Base


class LegalDomain(BaseDomain):
    """Domain wiring for legal contract review."""

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
            "get_contract_section": {
                "schema": defs.GetContractSectionArgs,
                "func": impl.get_contract_section,
            },
            "extract_clause": {
                "schema": defs.ExtractClauseArgs,
                "func": impl.extract_clause,
            },
            "flag_risk": {
                "schema": defs.FlagRiskArgs,
                "func": impl.flag_risk,
            },
            "get_standard_terms": {
                "schema": defs.GetStandardTermsArgs,
                "func": impl.get_standard_terms,
            },
            "compare_clause": {
                "schema": defs.CompareClauseArgs,
                "func": impl.compare_clause,
            },
            "add_memo_note": {
                "schema": defs.AddMemoNoteArgs,
                "func": impl.add_memo_note,
            },
            "finalize_memo": {
                "schema": defs.FinalizeMemoArgs,
                "func": impl.finalize_memo,
            },
        }

    def get_tasks(self) -> list[dict]:
        return TASKS

    def compute_step_reward(
        self, tool_name: str, tool_result: str, session: Session, step_count: int
    ) -> float:
        result_lower = tool_result.lower()
        if "not found" in result_lower or "error" in result_lower:
            return -0.05
        if tool_name == "finalize_memo" and "finalized" in result_lower:
            return 0.40
        if tool_name == "flag_risk" and "flagged" in result_lower:
            return 0.20
        if tool_name == "compare_clause":
            return 0.15
        if tool_name == "add_memo_note" and "added" in result_lower:
            return 0.10
        if tool_name in ("get_contract_section", "extract_clause", "get_standard_terms"):
            return 0.05
        return 0.0

    def is_done(self, tool_name: str, tool_result: str, session: Session) -> bool:
        return tool_name == "finalize_memo" and "finalized" in tool_result.lower()

    def get_graders(self) -> list[BaseGrader]:
        return [LegalCodeGrader(), LegalLLMGrader()]

    def get_system_prompt_template(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE
