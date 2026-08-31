#!/bin/sh
set -eu
export BAO_ADDR="${BAO_ADDR:-http://openbao:8200}"
TOKEN_FILE="${OPENBAO_TOKEN_FILE:-/run/openbao/token}"
while true; do
  if [ -s "$TOKEN_FILE" ]; then
    export BAO_TOKEN="$(cat "$TOKEN_FILE")"
    bao token renew -self >/dev/null
    unset BAO_TOKEN
  fi
  sleep "${RENEW_INTERVAL_SECONDS:-600}"
done
