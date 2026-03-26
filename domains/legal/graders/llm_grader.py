"""LLM-based legal grader."""

from __future__ import annotations

import json
import os
from typing import Any

from server.interfaces import BaseGrader

try:
    import openai
except ModuleNotFoundError:
    openai = None  # type: ignore[assignment]


class LegalLLMGrader(BaseGrader):
    """LLM grader that rates memo notes."""

    def grade(self, trajectory: list[dict[str, Any]], session: Any) -> dict[str, Any]:
        note = self._find_last_note(trajectory)
        if note is None:
            return {"score": 0.3, "success": False, "feedback": "No memo note found"}
        if "OPENAI_API_KEY" not in os.environ or openai is None:
            return {"score": 0.5, "success": True, "feedback": "No API key — neutral score"}
        return self._grade_with_openai(note.get("tool_args", {}).get("note", ""))

    def _find_last_note(self, trajectory: list[dict[str, Any]]) -> dict[str, Any] | None:
        for step in reversed(trajectory):
            if step["tool_name"] == "add_memo_note":
                return step
        return None

    def _grade_with_openai(self, text: str) -> dict[str, Any]:
        prompt = (
            "Rate this legal memo note 0.0-1.0. "
            "0.0 is vague, 1.0 is precise and actionable. "
            f"Memo note: {text}\nRespond JSON: {{\"score\": float, \"reason\": string}}"
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
            return {"score": 0.4, "success": False, "feedback": f"LLM error: {exc}"}
