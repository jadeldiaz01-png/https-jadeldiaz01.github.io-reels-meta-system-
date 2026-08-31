#!/usr/bin/env sh
set -eu
: "${BAO_ADDR:=http://127.0.0.1:8200}"
: "${BAO_TOKEN:=sandbox-root}"
export BAO_ADDR BAO_TOKEN

bao secrets enable -path=secret kv-v2 2>/dev/null || true
bao policy write revenue-engine - <<'EOF'
path "secret/data/revenue-engine/*" {
  capabilities = ["read"]
}
EOF

bao auth enable approle 2>/dev/null || true
bao write auth/approle/role/revenue-engine \
  token_policies="revenue-engine" \
  token_ttl="15m" \
  token_max_ttl="1h" \
  secret_id_ttl="15m"

bao kv put secret/revenue-engine/sandbox marker="sandbox-only"
echo "OpenBao sandbox policy and AppRole configured. Do not reuse the dev root token in production."
