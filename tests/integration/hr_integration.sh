#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="${VENV_PATH:-/Users/yohaankhan/Desktop/trialect/venv/bin/activate}"
PORT="${PORT:-7860}"
DATABASE_PATH="${DATABASE_PATH:-$ROOT_DIR/hr_test.db}"
DATABASE_URL="sqlite:///./$(basename "$DATABASE_PATH")"
SERVER_LOG="${SERVER_LOG:-$ROOT_DIR/tests/integration/hr_server.log}"

if [[ ! -f "$VENV_PATH" ]]; then
  echo "Virtualenv activate script not found at: $VENV_PATH" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$DATABASE_PATH" "${DATABASE_PATH}-journal"
}

assert_json() {
  local label="$1"
  local payload="$2"
  local check_code="$3"
  local indented_check_code

  indented_check_code="$(printf '%s\n' "$check_code" | sed 's/^/    /')"

  JSON_LABEL="$label" JSON_PAYLOAD="$payload" python3 - <<PY
import json
import os
import sys

label = os.environ["JSON_LABEL"]
payload = os.environ["JSON_PAYLOAD"]
try:
    data = json.loads(payload)
except Exception as exc:
    print(f"{label} returned invalid JSON: {exc}", file=sys.stderr)
    print(payload, file=sys.stderr)
    raise SystemExit(1)

try:
${indented_check_code}
except Exception:
    print(f"{label} assertion failed. Payload was:", file=sys.stderr)
    print(json.dumps(data, indent=2), file=sys.stderr)
    raise

print(f"{label}: OK")
PY
}

trap cleanup EXIT

cd "$ROOT_DIR"
source "$VENV_PATH"

rm -f "$DATABASE_PATH" "${DATABASE_PATH}-journal" "$SERVER_LOG"

echo "Starting HR server on port $PORT..."
DOMAIN=hr DATABASE_URL="$DATABASE_URL" PYTHONPATH=. python3 -m uvicorn server.app:app --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

for _ in {1..30}; do
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Server did not become ready. Log output:" >&2
  cat "$SERVER_LOG" >&2
  exit 1
fi

HEALTH="$(curl -s "http://127.0.0.1:$PORT/health")"
assert_json "health" "$HEALTH" '
assert data["status"] in {"ok", "healthy"}
if "domain" in data:
    assert data["domain"] == "hr"
if "registered_domains" in data:
    assert "hr" in data["registered_domains"]
'

TASKS="$(curl -s "http://127.0.0.1:$PORT/tasks")"
assert_json "tasks" "$TASKS" '
assert data["domain"] == "hr"
assert len(data["tasks"]) == 3
assert {task["difficulty"] for task in data["tasks"]} == {"easy", "medium", "hard"}
assert "properties" in data["action_schema"]
'

python3 - <<PY
from client import MultiDomainEnv
from models import EnvAction

env = MultiDomainEnv(base_url="http://127.0.0.1:${PORT}").sync()

def debug_step(label, step):
    print(
        f"{label} payload:",
        {
            "reward": step.reward,
            "done": step.done,
            "content": step.observation.content,
            "info": step.observation.info,
        },
    )

with env:
    reset = env.reset()
    debug_step("reset_easy", reset)
    assert reset.done is False
    assert reset.reward == 0.0
    assert reset.observation.info["task_id"] == "hr_easy"
    print("reset_easy: OK")

    step_1 = env.step(
        EnvAction(
            tool_name="lookup_policy",
            tool_args={"topic": "annual_leave"},
            thought="Retrieve the leave policy first.",
        )
    )
    debug_step("step_1", step_1)
    assert step_1.done is False
    assert abs((step_1.reward or 0.0) - 0.05) < 1e-9
    assert "Annual Leave Policy" in step_1.observation.content
    print("step_1: OK")

    reset_medium = env.reset()
    debug_step("reset_medium", reset_medium)
    assert reset_medium.observation.info["task_id"] == "hr_medium"
    print("reset_medium: OK")

    step_2 = env.step(
        EnvAction(
            tool_name="check_leave_balance",
            tool_args={"employee_id": "E-202", "leave_type": "annual"},
            thought="Confirm the employee has enough leave balance.",
        )
    )
    debug_step("step_2", step_2)
    assert step_2.done is False
    assert "E-202" in step_2.observation.content
    print("step_2: OK")

    step_3 = env.step(
        EnvAction(
            tool_name="file_leave_request",
            tool_args={
                "employee_id": "E-202",
                "leave_type": "annual",
                "start_date": "2024-07-15",
                "end_date": "2024-07-19",
                "days_requested": 5,
                "reason": "Family trip",
            },
            thought="File the leave request once balance is confirmed.",
        )
    )
    debug_step("step_3", step_3)
    assert "Reference number:" in step_3.observation.content
    ref = step_3.observation.content.split("Reference number:", 1)[1].split(".", 1)[0].strip()
    print("step_3: OK")

    step_4 = env.step(
        EnvAction(
            tool_name="send_hr_notification",
            tool_args={
                "employee_id": "E-202",
                "recipient": "manager",
                "message": f"Leave request {ref} has been filed for review.",
            },
            thought="Notify the manager with the generated reference.",
        )
    )
    debug_step("step_4", step_4)
    assert step_4.done is False
    assert abs((step_4.reward or 0.0) - 0.10) < 1e-9
    print("step_4: OK")

    step_5 = env.step(
        EnvAction(
            tool_name="close_hr_request",
            tool_args={
                "request_ref": ref,
                "resolution": "Leave request logged and manager notified.",
            },
            thought="Close the HR request with the actual reference number.",
        )
    )
    debug_step("step_5", step_5)
    assert step_5.done is True
    assert abs((step_5.reward or 0.0) - 0.40) < 1e-9
    assert step_5.observation.info["grader_score"] is not None
    print("step_5: OK")
PY

echo "Running openenv validate..."
DOMAIN=hr PYTHONPATH=. openenv validate --verbose

echo
echo "HR integration smoke test passed."
