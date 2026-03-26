#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="${VENV_PATH:-/Users/yohaankhan/Desktop/trialect/venv/bin/activate}"
PORT="${PORT:-7860}"
DATABASE_PATH="${DATABASE_PATH:-$ROOT_DIR/saas_test.db}"
DATABASE_URL="sqlite:///./$(basename "$DATABASE_PATH")"
SERVER_LOG="${SERVER_LOG:-$ROOT_DIR/tests/integration/saas_server.log}"

if [[ ! -f "$VENV_PATH" ]]; then
  echo "Virtualenv activate script not found at: $VENV_PATH" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -f "$DATABASE_PATH"
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
except AssertionError:
    print(f"{label} assertion failed. Payload was:", file=sys.stderr)
    print(json.dumps(data, indent=2), file=sys.stderr)
    raise

print(f"{label}: OK")
PY
}

assert_observation_json() {
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
    raw = json.loads(payload)
except Exception as exc:
    print(f"{label} returned invalid JSON: {exc}", file=sys.stderr)
    print(payload, file=sys.stderr)
    raise SystemExit(1)

observation = raw.get("observation", {})
if isinstance(observation, dict):
    data = dict(observation)
else:
    data = {}

for key in ("reward", "done", "info", "content"):
    if key in raw and key not in data:
        data[key] = raw[key]

try:
${indented_check_code}
except Exception:
    print(f"{label} assertion failed. Payload was:", file=sys.stderr)
    print(json.dumps(raw, indent=2), file=sys.stderr)
    raise

print(f"{label}: OK")
PY
}

trap cleanup EXIT

cd "$ROOT_DIR"
source "$VENV_PATH"

rm -f "$DATABASE_PATH" "$SERVER_LOG"

echo "Starting SaaS server on port $PORT..."
DOMAIN=saas DATABASE_URL="$DATABASE_URL" PYTHONPATH=. python3 -m uvicorn server.app:app --port "$PORT" >"$SERVER_LOG" 2>&1 &
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
    assert data["domain"] == "saas"
if "registered_domains" in data:
    assert "saas" in data["registered_domains"]
'

TASKS="$(curl -s "http://127.0.0.1:$PORT/tasks")"
assert_json "tasks" "$TASKS" '
assert data["domain"] == "saas"
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
    assert "Task:" in reset.observation.content
    assert "task_id" in reset.observation.info
    print("reset: OK")

    step_1 = env.step(
        EnvAction(
            tool_name="search_tickets",
            tool_args={"query": "billing", "customer_id": "C-1042"},
            thought="Looking up the ticket",
        )
    )
    debug_step("step_1", step_1)
    assert step_1.done is False
    assert abs((step_1.reward or 0.0) - 0.05) < 1e-9
    assert "T-5001" in step_1.observation.content
    print("step_1: OK")

    step_2 = env.step(
        EnvAction(
            tool_name="close_ticket",
            tool_args={
                "ticket_id": "T-5001",
                "resolution": "Billing error confirmed and corrected",
            },
            thought="Closing the ticket",
        )
    )
    debug_step("step_2", step_2)
    assert step_2.done is True
    assert abs((step_2.reward or 0.0) - 0.40) < 1e-9
    assert step_2.observation.info["grader_score"] is not None
    print("step_2: OK")
PY

GRADER="$(curl -s -X POST "http://127.0.0.1:$PORT/grader" \
  -H "Content-Type: application/json" \
  -d "{\"trajectory\":[{\"step_idx\":1,\"tool_name\":\"search_tickets\",\"tool_args\":{\"query\":\"billing\",\"customer_id\":\"C-1042\"},\"thought\":\"\",\"result\":\"Found T-5001\",\"reward\":0.05},{\"step_idx\":2,\"tool_name\":\"close_ticket\",\"tool_args\":{\"ticket_id\":\"T-5001\",\"resolution\":\"Resolved\"},\"thought\":\"\",\"result\":\"Ticket T-5001 closed.\",\"reward\":0.4}]}")"
assert_json "grader" "$GRADER" '
assert data["final_score"] >= 0.6
assert len(data["results"]) >= 1
'

echo "Running openenv validate..."
DOMAIN=saas PYTHONPATH=. openenv validate --verbose

echo
echo "SaaS integration test passed."
