#!/usr/bin/env bash
# End-to-end smoke test: builds container and exercises HTTP endpoints across domains.
set -euo pipefail

IMAGE="multidomain-env-e2e-test"
PASS=0
FAIL=0

pass() {
  echo "  ✓ $1"
  PASS=$((PASS + 1))
}

fail() {
  echo "  ✗ $1"
  FAIL=$((FAIL + 1))
}

echo "Building Docker image..."
docker build -f server/Dockerfile -t "$IMAGE" .

for DOMAIN in saas hr legal; do
  echo ""
  echo "=== DOMAIN=$DOMAIN ==="

  CID=$(
    docker run -d -p 7860:7860 \
      -e DOMAIN="$DOMAIN" \
      -e DATABASE_URL="sqlite:///./env.db" \
      "$IMAGE"
  )

  cleanup() {
    docker stop "$CID" >/dev/null 2>&1 || true
    docker rm "$CID" >/dev/null 2>&1 || true
  }

  trap cleanup EXIT

  for i in $(seq 1 30); do
    if curl -sf http://localhost:7860/health >/dev/null 2>&1; then
      break
    fi
    sleep 1
    if [ "$i" -eq 30 ]; then
      fail "$DOMAIN: server did not start in 30s"
      cleanup
      continue 2
    fi
  done

  HEALTH=$(curl -sf http://localhost:7860/health)
  echo "$HEALTH" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] in {'ok','healthy'}, f'Bad status: {d}'
if 'domain' in d:
    assert d['domain'] == '$DOMAIN', f'Wrong domain: {d}'
" && pass "$DOMAIN: /health" || fail "$DOMAIN: /health"

  TASKS=$(curl -sf http://localhost:7860/tasks)
  echo "$TASKS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert len(d['tasks']) == 3, f'Expected 3 tasks, got {len(d['tasks'])}'
assert {t['difficulty'] for t in d['tasks']} == {'easy','medium','hard'}
assert 'action_schema' in d
" && pass "$DOMAIN: /tasks (3 tasks, easy/medium/hard)" || fail "$DOMAIN: /tasks"

  ./../venv/bin/python - <<PY && pass "$DOMAIN: client reset/step/state" || fail "$DOMAIN: client reset/step/state"
from client import MultiDomainEnv
from models import EnvAction

env = MultiDomainEnv(base_url="http://127.0.0.1:7860").sync()
with env:
    reset = env.reset()
    assert reset.done is False, reset
    assert reset.reward == 0.0, reset
    assert reset.observation.content, reset
    assert "task_id" in reset.observation.info, reset.observation.info

    state_before = env.state()
    assert "episode_id" in state_before or "step_count" in state_before, state_before

    step = env.step(
        EnvAction(
            tool_name="definitely_not_a_real_tool",
            tool_args={},
            thought="",
        )
    )
    assert step.reward == -0.05, step
    assert step.done is False, step
    assert "not a valid tool" in step.observation.content, step.observation.content

    state_after = env.state()
    assert state_after["step_count"] >= 1, state_after
PY

  GRADER=$(curl -sf -X POST http://localhost:7860/grader \
    -H "Content-Type: application/json" \
    -d '{"trajectory":[]}')
  echo "$GRADER" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'final_score' in d
assert 0.0 <= d['final_score'] <= 1.0
" && pass "$DOMAIN: /grader" || fail "$DOMAIN: /grader"

  cleanup
  trap - EXIT
done

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
  echo "SOME TESTS FAILED"
  exit 1
fi
echo "ALL E2E TESTS PASSED"
