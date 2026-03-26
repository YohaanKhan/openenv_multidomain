#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="${VENV_PATH:-/Users/yohaankhan/Desktop/trialect/venv/bin/activate}"
PORT="${PORT:-7860}"
DATABASE_PATH="${DATABASE_PATH:-$ROOT_DIR/legal_test.db}"
DATABASE_URL="sqlite:///./$(basename "$DATABASE_PATH")"
SERVER_LOG="${SERVER_LOG:-$ROOT_DIR/tests/integration/legal_server.log}"

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

echo "Starting Legal server on port $PORT..."
DOMAIN=legal DATABASE_URL="$DATABASE_URL" PYTHONPATH=. python3 -m uvicorn server.app:app --port "$PORT" >"$SERVER_LOG" 2>&1 &
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
    assert data["domain"] == "legal"
if "registered_domains" in data:
    assert "legal" in data["registered_domains"]
'

TASKS="$(curl -s "http://127.0.0.1:$PORT/tasks")"
assert_json "tasks" "$TASKS" '
assert data["domain"] == "legal"
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
    debug_step("reset", reset)
    assert reset.done is False
    assert reset.reward == 0.0
    assert reset.observation.info["task_id"] == "legal_easy"
    print("reset: OK")

    step_1 = env.step(
        EnvAction(
            tool_name="extract_clause",
            tool_args={"contract_id": "NDA-001", "clause_type": "termination"},
            thought="Pull the termination clause for review.",
        )
    )
    debug_step("step_1", step_1)
    assert step_1.done is False
    assert abs((step_1.reward or 0.0) - 0.05) < 1e-9
    assert "NDA-001-TERM" in step_1.observation.content
    print("step_1: OK")

    step_2 = env.step(
        EnvAction(
            tool_name="add_memo_note",
            tool_args={
                "contract_id": "NDA-001",
                "section": "termination",
                "note": "Termination clause allows either party to terminate with 30 days notice.",
            },
            thought="Add the clause summary to the memo.",
        )
    )
    debug_step("step_2", step_2)
    assert step_2.done is False
    assert abs((step_2.reward or 0.0) - 0.10) < 1e-9
    print("step_2: OK")

    step_3 = env.step(
        EnvAction(
            tool_name="finalize_memo",
            tool_args={
                "contract_id": "NDA-001",
                "summary": "Termination clause reviewed and memo completed.",
            },
            thought="Finalize the memo after capturing the finding.",
        )
    )
    debug_step("step_3", step_3)
    assert step_3.done is True
    assert abs((step_3.reward or 0.0) - 0.40) < 1e-9
    assert step_3.observation.info["grader_score"] is not None
    print("step_3: OK")
PY

echo "Running openenv validate..."
DOMAIN=legal PYTHONPATH=. openenv validate --verbose

echo
echo "Legal integration test passed."
