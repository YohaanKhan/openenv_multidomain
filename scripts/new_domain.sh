#!/usr/bin/env bash
# Scaffold a new domain plugin in < 30 seconds
# Usage: bash scripts/new_domain.sh <domain_name>
# Example: bash scripts/new_domain.sh finance
set -euo pipefail

DOMAIN_NAME="${1:?Usage: bash scripts/new_domain.sh <domain_name>}"

# Validate name is lowercase alphanumeric
if ! echo "$DOMAIN_NAME" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "ERROR: Domain name must be lowercase alphanumeric (got: $DOMAIN_NAME)"
    exit 1
fi

# PascalCase for class name: finance -> Finance, my_domain -> MyDomain
CLASS_NAME=$(
    echo "$DOMAIN_NAME" | awk -F_ '
        {
            out = ""
            for (i = 1; i <= NF; i++) {
                out = out toupper(substr($i, 1, 1)) substr($i, 2)
            }
            print out
        }
    '
)
DOMAIN_PATH="domains/${DOMAIN_NAME}"

if [ -d "$DOMAIN_PATH" ]; then
    echo "ERROR: Domain '$DOMAIN_NAME' already exists at $DOMAIN_PATH"
    exit 1
fi

echo "Scaffolding domain: $DOMAIN_NAME (class: ${CLASS_NAME}Domain)"

mkdir -p "${DOMAIN_PATH}/tools" "${DOMAIN_PATH}/graders"

cat > "${DOMAIN_PATH}/__init__.py" <<EOF
from server.domain_registry import DomainRegistry
from domains.${DOMAIN_NAME}.domain import ${CLASS_NAME}Domain

DomainRegistry.register("${DOMAIN_NAME}", ${CLASS_NAME}Domain)
EOF

cat > "${DOMAIN_PATH}/schema.py" <<EOF
# SQLAlchemy ORM models for the ${DOMAIN_NAME} domain
# All table names must be prefixed "${DOMAIN_NAME}_" to avoid collisions
from sqlalchemy import Column, String, Text, Integer, Float, Boolean
from server.utils.db import Base


# TODO: Define your tables here
# class ${CLASS_NAME}Record(Base):
#     __tablename__ = "${DOMAIN_NAME}_records"
#     id = Column(String, primary_key=True)
#     content = Column(Text, default="")
EOF

cat > "${DOMAIN_PATH}/tools/definitions.py" <<EOF
# Pydantic tool argument schemas - these are what the agent sees in the system prompt
# Class docstrings become tool descriptions. Field descriptions become argument docs.
from pydantic import BaseModel, Field
from typing import Optional


# TODO: Define your tool schemas here
# class ExampleToolArgs(BaseModel):
#     """One-line description of what this tool does."""
#     param: str = Field(..., description="What this parameter is for")
EOF

cat > "${DOMAIN_PATH}/tools/implementation.py" <<EOF
# Pure tool functions: (validated_args_instance, session) -> str
# Rules:
#   - Always return str (human-readable text the agent reads)
#   - Never raise - catch errors and return error strings
#   - Use session.flush() after mutations
#   - No global state, no imports of engine
from sqlalchemy.orm import Session


# TODO: Implement your tools here
# from domains.${DOMAIN_NAME}.tools.definitions import ExampleToolArgs
#
# def example_tool(args: ExampleToolArgs, session: Session) -> str:
#     return f"Example result for: {args.param}"
EOF

cat > "${DOMAIN_PATH}/tasks.py" <<EOF
# Task definitions and seed data for the ${DOMAIN_NAME} domain
# Must have exactly 3 tasks: one easy, one medium, one hard
from sqlalchemy.orm import Session

TASKS = [
    {
        "id": "${DOMAIN_NAME}_easy",
        "name": "TODO: Easy Task Name",
        "difficulty": "easy",
        "max_steps": 5,
        "description": "TODO: Describe what the agent must accomplish",
    },
    {
        "id": "${DOMAIN_NAME}_medium",
        "name": "TODO: Medium Task Name",
        "difficulty": "medium",
        "max_steps": 12,
        "description": "TODO: Describe the multi-step task",
    },
    {
        "id": "${DOMAIN_NAME}_hard",
        "name": "TODO: Hard Task Name",
        "difficulty": "hard",
        "max_steps": 20,
        "description": "TODO: Describe the complex task",
    },
]


def seed(task_id: str, session: Session) -> dict:
    """
    Insert seed data for a task inside the current transaction savepoint.
    Use session.merge() not session.add() - must be idempotent.
    """
    if task_id == "${DOMAIN_NAME}_easy":
        # TODO: session.merge(YourModel(id="...", ...))
        session.flush()
        return {"task_id": task_id}
    elif task_id == "${DOMAIN_NAME}_medium":
        session.flush()
        return {"task_id": task_id}
    elif task_id == "${DOMAIN_NAME}_hard":
        session.flush()
        return {"task_id": task_id}
    raise ValueError(f"Unknown task_id: {task_id}")
EOF

cat > "${DOMAIN_PATH}/prompts.py" <<EOF
# System prompt template for the ${DOMAIN_NAME} domain
# {tool_docs} is filled automatically by SystemPromptBuilder from your tool schemas
SYSTEM_PROMPT_TEMPLATE = """\
You are a ${DOMAIN_NAME} assistant. Use the tools below to complete your task.

Guidelines:
- TODO: Add domain-specific guidelines here

Available tools:
{tool_docs}\\
"""
EOF

cat > "${DOMAIN_PATH}/graders/code_grader.py" <<EOF
# Deterministic code grader for the ${DOMAIN_NAME} domain
# Must work with session=None (called from /grader endpoint without live DB)
# Must be deterministic: same trajectory -> same score always
from server.interfaces import BaseGrader
from sqlalchemy.orm import Session


class ${CLASS_NAME}CodeGrader(BaseGrader):

    def grade(self, trajectory: list[dict], session: Session | None) -> dict:
        """
        Score a completed episode trajectory.
        Return {"score": float 0.0-1.0, "success": bool, "feedback": str}
        """
        tools_called = [step["tool_name"] for step in trajectory]
        # TODO: Implement task-specific grading logic
        # Example: check if the right tools were called in the right order
        score = 0.0
        feedback = f"Tools called: {tools_called}"
        success = False
        return {"score": round(score, 4), "success": success, "feedback": feedback}
EOF

cat > "${DOMAIN_PATH}/graders/llm_grader.py" <<EOF
# LLM-as-judge grader for the ${DOMAIN_NAME} domain
# Falls back gracefully if OPENAI_API_KEY is not set
import os
import json
from server.interfaces import BaseGrader
from sqlalchemy.orm import Session


class ${CLASS_NAME}LLMGrader(BaseGrader):

    def grade(self, trajectory: list[dict], session: Session | None) -> dict:
        # Find the last relevant agent output to evaluate
        # TODO: Adjust to find the right step type for your domain
        relevant_output = ""
        for step in reversed(trajectory):
            if step["tool_name"] in ("send_email", "add_memo_note", "send_hr_notification"):
                relevant_output = step.get("result", "")
                break

        if not relevant_output:
            return {"score": 0.3, "success": False, "feedback": "No evaluable output found"}

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"score": 0.5, "success": True, "feedback": "No API key - defaulting to neutral"}

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                "Rate this agent output 0.0-1.0 where 1.0=excellent, 0.5=adequate, 0.0=poor.\\n"
                f"Output: \\"{relevant_output}\\"\\n"
                'Reply ONLY with JSON: {"score": <float>, "reason": "<string>"}'
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=150,
            )
            result = json.loads(resp.choices[0].message.content)
            score = max(0.0, min(1.0, float(result["score"])))
            return {"score": round(score, 4), "success": score >= 0.6, "feedback": result.get("reason", "")}
        except Exception as e:
            return {"score": 0.4, "success": False, "feedback": f"LLM grader error: {e}"}
EOF

cat > "${DOMAIN_PATH}/domain.py" <<EOF
# ${CLASS_NAME}Domain - wires all components to BaseDomain interface
# This file is pure wiring - all logic lives in schema, tools, tasks, graders
from sqlalchemy.orm import Session
from server.interfaces import BaseDomain, BaseGrader
from server.utils.db import Base
from domains.${DOMAIN_NAME} import schema  # noqa: registers ORM models with Base
from domains.${DOMAIN_NAME}.tasks import TASKS, seed as seed_task
from domains.${DOMAIN_NAME}.prompts import SYSTEM_PROMPT_TEMPLATE
from domains.${DOMAIN_NAME}.tools import definitions as defs
from domains.${DOMAIN_NAME}.tools import implementation as impl
from domains.${DOMAIN_NAME}.graders.code_grader import ${CLASS_NAME}CodeGrader
from domains.${DOMAIN_NAME}.graders.llm_grader import ${CLASS_NAME}LLMGrader


class ${CLASS_NAME}Domain(BaseDomain):

    def create_tables(self, engine) -> None:
        Base.metadata.create_all(engine)

    def seed_episode(self, task_id: str, session: Session) -> dict:
        return seed_task(task_id, session)

    def get_tools(self) -> dict[str, dict]:
        return {}  # TODO: map tool names to {"schema": defs.XArgs, "func": impl.x}

    def get_tasks(self) -> list[dict]:
        return TASKS

    def compute_step_reward(
        self, tool_name: str, tool_result: str, session: Session, step_count: int
    ) -> float:
        result_lower = tool_result.lower()
        if "not found" in result_lower or "error" in result_lower:
            return -0.05
        # TODO: Add domain-specific reward shaping
        return 0.05

    def is_done(self, tool_name: str, tool_result: str, session: Session) -> bool:
        # TODO: Return True when the episode should end
        # Example: return tool_name == "close_request" and "closed" in tool_result.lower()
        return False

    def get_graders(self) -> list[BaseGrader]:
        return [${CLASS_NAME}CodeGrader(), ${CLASS_NAME}LLMGrader()]

    def get_system_prompt_template(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE
EOF

touch "${DOMAIN_PATH}/tools/__init__.py"
touch "${DOMAIN_PATH}/graders/__init__.py"

IMPORT_LINE="from domains import ${DOMAIN_NAME}  # noqa: F401"
if ! grep -Fxq "$IMPORT_LINE" "domains/__init__.py"; then
    echo "$IMPORT_LINE" >> "domains/__init__.py"
fi

echo ""
echo "Done! Scaffold created at: ${DOMAIN_PATH}"
echo ""
echo "Files to fill in (in this order):"
echo "  1. ${DOMAIN_PATH}/schema.py          - SQLAlchemy table models"
echo "  2. ${DOMAIN_PATH}/tools/definitions.py - Pydantic arg schemas"
echo "  3. ${DOMAIN_PATH}/tools/implementation.py - Tool functions"
echo "  4. ${DOMAIN_PATH}/tasks.py            - Task definitions + seed data"
echo "  5. ${DOMAIN_PATH}/graders/code_grader.py - Grader logic"
echo "  6. ${DOMAIN_PATH}/domain.py           - Wire get_tools(), is_done(), compute_step_reward()"
echo ""
echo "Zero engine changes needed. Just fill the TODOs above."
