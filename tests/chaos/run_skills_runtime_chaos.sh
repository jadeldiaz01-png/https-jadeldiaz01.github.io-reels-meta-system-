#!/bin/sh
set -eu

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.e2e.yml"
API="${E2E_SKILLS_RUNTIME_URL:-http://127.0.0.1:18010}"
H1='X-Authenticated-Subject: chaos-human'
H2='X-Actor-Type: human'
TARGET="$API/v1/skills/e2e-skill/1.0.0/authorize-execution"

expect_denied() {
  code="$(curl -sS -o /tmp/skills-chaos-body -w '%{http_code}' -X POST -H "$H1" -H "$H2" "$TARGET" || true)"
  if [ "$code" = "200" ]; then
    echo "FAIL: execution authorized during dependency fault"
    cat /tmp/skills-chaos-body || true
    exit 1
  fi
}

trap '$COMPOSE unpause opa openbao >/dev/null 2>&1 || true' EXIT

$COMPOSE pause openbao
expect_denied
$COMPOSE unpause openbao

$COMPOSE pause opa
expect_denied
$COMPOSE unpause opa

echo "chaos fail-closed checks passed"
