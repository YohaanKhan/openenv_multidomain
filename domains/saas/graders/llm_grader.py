"""LLM-based fallback grader for the SaaS domain’s customer-facing emails."""

from __future__ import annotations

import json
import os
from typing import Iterable

from server.interfaces import BaseGrader


class SaaSLLMGrader(BaseGrader):
    """Calls an LLM to judge the tone and helpfulness of the final SaaS deferral email."""

    def grade(self, trajectory: list[dict], session) -> dict:
        email_step = self._find_latest_email(trajectory)
        if email_step is None:
            return {
                "score": 0.5,
                "success": True,
                "feedback": "No customer-facing email to evaluate for this trajectory",
            }
        if not os.environ.get("OPENAI_API_KEY"):
            return {
                "score": 0.5,
                "success": True,
                "feedback": "No API key — defaulting to neutral score",
            }
        try:
            import openai

            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Rate the following customer-facing email on a scale from 0.0 to 1.0. "
                            "1.0 = professional, empathetic, and correctly handles the request. "
                            "0.5 = adequate but generic. "
                            "0.0 = rude, incorrect, or unhelpful."
                        ),
                    },
                    {
                        "role": "user",
                        "content": email_step["tool_args"].get("body", ""),
                    },
                ],
                response_format={
                    "type": "json_object",
                    "json_schema": {
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"},
                    },
                },
            )
            payload = response.choices[0].message.content
            if isinstance(payload, dict):
                parsed = payload
            else:
                parsed = json.loads(payload)
            score = float(parsed.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            return {
                "score": score,
                "success": score >= 0.5,
                "feedback": parsed.get("reason", "LLM provided no reason."),
            }
        except Exception as exc:
            return {
                "score": 0.4,
                "success": False,
                "feedback": f"LLM grader error: {exc}",
            }

    def _find_latest_email(self, trajectory: Iterable[dict]) -> dict | None:
        for step in reversed(trajectory):
            if step.get("tool_name") == "send_email":
                return step
        return None
