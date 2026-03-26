"\"\"\"LLM-based HR grader.\"\"\""

from __future__ import annotations

import json
import os
from typing import Any

from server.interfaces import BaseGrader

try:
    import openai
except ModuleNotFoundError:
    openai = None  # type: ignore[assignment]


class HRLLMGrader(BaseGrader):
    """LLM grader that evaluates the final HR notification."""

    def grade(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        notification = self._find_last_notification(trajectory)
        if notification is None:
            return {
                "score": 0.3,
                "success": False,
                "feedback": "No HR notification found",
            }
        if "OPENAI_API_KEY" not in os.environ or openai is None:
            return {
                "score": 0.5,
                "success": True,
                "feedback": "No API key — defaulting to neutral score",
            }
        message = notification.get("tool_args", {}).get("message", "")
        return self._grade_with_openai(message)

    def _find_last_notification(self, trajectory: list[dict[str, Any]]) -> dict[str, Any] | None:
        for step in reversed(trajectory):
            if step["tool_name"] == "send_hr_notification":
                return step
        return None

    def _grade_with_openai(self, text: str) -> dict[str, Any]:
        prompt = (
            "You are a professional HR reviewer. Rate the following notification 0.0-1.0.\n"
            "1.0 = professional, empathetic, resolves the employee's concern.\n"
            "0.5 = adequate but generic.\n"
            "0.0 = unprofessional or incorrect.\n"
            f"Notification: {text}\n"
            "Respond with JSON: {\"score\": float, \"reason\": string}"
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            score = max(0.0, min(1.0, float(data.get("score", 0.5))))
            return {"score": score, "success": True, "feedback": data.get("reason", "")}
        except Exception as exc:
            return {
                "score": 0.4,
                "success": False,
                "feedback": f"LLM grader error: {exc}",
            }
