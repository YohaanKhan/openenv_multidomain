"""Deterministic legal code grader."""

from __future__ import annotations

from typing import Any

from domains.legal import schema
from server.interfaces import BaseGrader


class LegalCodeGrader(BaseGrader):
    """Heuristic grader that mirrors the legal task checkpoints."""

    def grade(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        task = self._infer_task(trajectory)
        if task == "legal_easy":
            return self._grade_easy(trajectory)
        if task == "legal_medium":
            return self._grade_medium(trajectory, session)
        if task == "legal_hard":
            return self._grade_hard(trajectory, session)
        return {"score": 0.5, "success": False, "feedback": "Unknown legal task"}

    def _infer_task(self, trajectory: list[dict[str, Any]]) -> str:
        for step in trajectory:
            args = step.get("tool_args", {})
            for value in args.values():
                if isinstance(value, str) and "SA-001" in value:
                    return "legal_hard"
                if isinstance(value, str) and "VC-001" in value:
                    return "legal_medium"
        return "legal_easy"

    def _grade_easy(self, trajectory: list[dict[str, Any]]) -> dict[str, Any]:
        names = {step["tool_name"] for step in trajectory}
        score = 0.0
        if names.intersection({"extract_clause", "get_contract_section"}):
            score += 0.3
        if "add_memo_note" in names:
            score += 0.3
        if "finalize_memo" in names:
            score += 0.4
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": "finalize_memo" in names,
            "feedback": "Easy legal grader",
        }

    def _grade_medium(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        checklist = [
            "extract_clause",
            "compare_clause",
            "flag_risk",
            "finalize_memo",
        ]
        names = {step["tool_name"] for step in trajectory}
        score = sum(0.25 for name in checklist if name in names)
        success = {"flag_risk", "finalize_memo"}.issubset(names)
        if session is not None:
            clause = (
                session.query(schema.Clause)
                .filter_by(contract_id="VC-001", clause_type="payment")
                .first()
            )
            if clause and clause.risk_level != "none" and "flag_risk" in names:
                score = min(1.0, score + 0.05)
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": success,
            "feedback": "Medium legal grader",
        }

    def _grade_hard(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        names = [step["tool_name"] for step in trajectory]
        score = 0.0
        if names.count("extract_clause") >= 2 or "get_contract_section" in names:
            score += 0.15
        if names.count("compare_clause") >= 2:
            score += 0.20
        high_flag = self._flagged_with_level(trajectory, "high")
        medium_flag = self._flagged_with_level(trajectory, "medium")
        if high_flag:
            score += 0.20
        if medium_flag:
            score += 0.20
        if "finalize_memo" in names:
            score += 0.25
        success = high_flag and medium_flag and "finalize_memo" in names
        if session is not None:
            indemnity = (
                session.query(schema.Clause)
                .filter_by(contract_id="SA-001", clause_type="indemnity")
                .first()
            )
            liability = (
                session.query(schema.Clause)
                .filter_by(contract_id="SA-001", clause_type="liability")
                .first()
            )
            if not (indemnity and liability):
                success = False
            else:
                success = success and indemnity.risk_level == "high" and liability.risk_level == "medium"
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": success,
            "feedback": "Hard legal grader",
        }

    def _flagged_with_level(self, trajectory: list[dict[str, Any]], level: str) -> bool:
        for step in trajectory:
            if step["tool_name"] != "flag_risk":
                continue
            args = step.get("tool_args", {})
            if args.get("risk_level", "").lower() == level:
                return True
        return False
