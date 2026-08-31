#!/bin/sh
set -eu

export BAO_ADDR="${BAO_ADDR:-http://openbao:8200}"
export BAO_TOKEN="${BAO_BOOTSTRAP_TOKEN:?BAO_BOOTSTRAP_TOKEN required only for sandbox bootstrap}"

until bao status >/dev/null 2>&1; do sleep 1; done

bao secrets list -format=json | grep -q '"transit/"' || bao secrets enable transit
bao read transit/keys/skills-runtime >/dev/null 2>&1 || bao write transit/keys/skills-runtime type=ecdsa-p256
bao policy write skills-runtime /config/skills-runtime-policy.hcl
bao policy write skills-bundle-signer /config/skills-bundle-signer-policy.hcl

mkdir -p /run/openbao
umask 077
TOKEN="$(bao token create -policy=skills-runtime -period=30m -orphan -field=token)"
printf '%s' "$TOKEN" > /run/openbao/token
unset BAO_TOKEN TOKEN

echo "skills-runtime OpenBao bootstrap complete; verifier workload token written to sink"
