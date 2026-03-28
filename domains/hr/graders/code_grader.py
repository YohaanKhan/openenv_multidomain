"\"\"\"Deterministic HR code grader.\"\"\""

from __future__ import annotations

from typing import Any

from server.interfaces import BaseGrader


class HRCodeGrader(BaseGrader):
    """Simple heuristic grader for the HR tasks."""

    def grade(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        task_id = self._infer_task(trajectory)
        if task_id == "hr_easy":
            return self._grade_easy(trajectory)
        if task_id == "hr_medium":
            return self._grade_medium(trajectory)
        if task_id == "hr_hard":
            return self._grade_hard(trajectory)
        return {"score": 0.5, "success": False, "feedback": "Could not infer HR task"}

    def _infer_task(self, trajectory: list[dict[str, Any]]) -> str:
        for step in trajectory:
            args = step.get("tool_args") or {}
            for value in args.values():
                if isinstance(value, str) and "E-303" in value:
                    return "hr_hard"
                if isinstance(value, str) and "E-202" in value:
                    return "hr_medium"
        return "hr_easy"

    def _grade_easy(self, trajectory: list[dict[str, Any]]) -> dict[str, Any]:
        tools = {step["tool_name"] for step in trajectory}
        score = 0.0
        if "lookup_policy" in tools:
            score += 0.4
        if "close_hr_request" in tools:
            score += 0.6
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": "close_hr_request" in tools,
            "feedback": "Easy task grader",
        }

    def _grade_medium(self, trajectory: list[dict[str, Any]]) -> dict[str, Any]:
        checklist = [
            ("check_leave_balance", 0.25),
            ("file_leave_request", 0.25),
            ("send_hr_notification", 0.25),
            ("close_hr_request", 0.25),
        ]
        tools = {step["tool_name"] for step in trajectory}
        score = sum(weight for name, weight in checklist if name in tools)
        success = {"file_leave_request", "close_hr_request"}.issubset(tools)
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": success,
            "feedback": "Medium task grader",
        }

    def _grade_hard(self, trajectory: list[dict[str, Any]]) -> dict[str, Any]:
        tools = [step["tool_name"] for step in trajectory]
        score = 0.0
        found_ref = self._extract_leave_ref(trajectory)
        if "lookup_policy" in tools:
            score += 0.15
        if "get_employee_record" in tools:
            score += 0.15
        if "get_benefits_summary" in tools:
            score += 0.20
        if "file_leave_request" in tools or any("dispute" in name for name in tools):
            score += 0.20
        close_idx = next(
            (idx for idx, step in enumerate(trajectory) if step["tool_name"] == "close_hr_request"), None
        )
        close_matches = (
            close_idx is not None
            and found_ref is not None
            and trajectory[close_idx].get("tool_args", {}).get("request_ref") == found_ref
        )
        if close_matches:
            score += 0.30
        success = close_matches and "file_leave_request" in tools
        return {
            "score": min(1.0, max(0.0, round(score, 4))),
            "success": success,
            "feedback": "Hard task grader",
        }

    def _extract_leave_ref(self, trajectory: list[dict[str, Any]]) -> str | None:
        for step in trajectory:
            if step["tool_name"] != "file_leave_request":
                continue
            result = step.get("result", "")
            marker = "Reference number:"
            if marker in result:
                candidate = result.split(marker, 1)[1].split(".", 1)[0].strip()
                if candidate:
                    return candidate
        return None
