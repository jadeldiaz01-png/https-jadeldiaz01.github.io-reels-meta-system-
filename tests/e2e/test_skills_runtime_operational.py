from __future__ import annotations

import base64
import hashlib
import json
import os

import httpx
import psycopg
import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_SKILLS_RUNTIME_E2E") != "1", reason="set RUN_SKILLS_RUNTIME_E2E=1")

DB = os.getenv("E2E_DATABASE_URL", "postgresql://engine:test@127.0.0.1:55432/revenue_engine")
API = os.getenv("E2E_SKILLS_RUNTIME_URL", "http://127.0.0.1:18010")
BAO = os.getenv("E2E_OPENBAO_URL", "http://127.0.0.1:18200")
BAO_TOKEN = os.getenv("BAO_DEV_ROOT_TOKEN", "")
HEADERS = {"X-Authenticated-Subject": "e2e-human", "X-Actor-Type": "human"}


def transit_sign(digest_hex: str) -> str:
    assert BAO_TOKEN, "BAO_DEV_ROOT_TOKEN required"
    payload = {"input": base64.b64encode(bytes.fromhex(digest_hex)).decode(), "prehashed": True}
    response = httpx.post(f"{BAO}/v1/transit/sign/skills-runtime/sha2-256", headers={"X-Vault-Token": BAO_TOKEN}, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()["data"]["signature"]


def seed_production_skill() -> tuple[str, str, str, str]:
    name, version = "e2e-skill", "1.0.0"
    bundle_digest = hashlib.sha256(b"immutable-e2e-bundle").hexdigest()
    signature = transit_sign(bundle_digest)
    manifest = {"name": name, "version": version, "self_promotion": False, "external_writes": False}
    evidence = {"review_passed": True, "tests_passed": True, "evals_passed": True, "security_passed": True, "policy_passed": True, "signature_verified": True, "critical_human_approval": True, "ci_run_id": "e2e"}
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO skill_registry(name,version,digest,stage,manifest,evidence,signature,signer_key,revision)
                VALUES (%s,%s,%s,'PRODUCTION',%s::jsonb,%s::jsonb,%s,'skills-runtime',5)
                ON CONFLICT (name,version) DO UPDATE SET stage='PRODUCTION', evidence=EXCLUDED.evidence, signature=EXCLUDED.signature, signer_key='skills-runtime'
            """, (name, version, hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), json.dumps(manifest), json.dumps(evidence), signature))
            cur.execute("DELETE FROM skill_bundles WHERE skill_name=%s AND version=%s", (name, version))
            cur.execute("""
                INSERT INTO skill_bundles(skill_name,version,bundle_digest,manifest_digest,signature,signer_key)
                VALUES (%s,%s,%s,%s,%s,'skills-runtime')
            """, (name, version, bundle_digest, hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), signature))
            cur.execute("""
                INSERT INTO skill_runtime_controls(skill_name,version,enabled,revoked,reason,updated_by)
                VALUES (%s,%s,TRUE,FALSE,'e2e-seed','e2e')
                ON CONFLICT (skill_name,version) DO UPDATE SET enabled=TRUE, revoked=FALSE, reason='e2e-seed', updated_by='e2e'
            """, (name, version))
    return name, version, bundle_digest, signature


def test_authorize_then_kill_switch_blocks_execution():
    name, version, _, _ = seed_production_skill()
    ok = httpx.post(f"{API}/v1/skills/{name}/{version}/authorize-execution", headers=HEADERS, timeout=15)
    assert ok.status_code == 200, ok.text
    assert ok.json()["execution_id"]
    disabled = httpx.put(f"{API}/v1/skills/{name}/{version}/control", headers=HEADERS, json={"enabled": False, "reason": "e2e-kill-switch"}, timeout=5)
    assert disabled.status_code == 200, disabled.text
    denied = httpx.post(f"{API}/v1/skills/{name}/{version}/authorize-execution", headers=HEADERS, timeout=5)
    assert denied.status_code == 403
    assert "skill_kill_switch_disabled" in denied.text
    restored = httpx.put(f"{API}/v1/skills/{name}/{version}/control", headers=HEADERS, json={"enabled": True, "reason": "e2e-restore"}, timeout=5)
    assert restored.status_code == 200


def test_tampered_bundle_signature_fails_closed():
    name, version, original, signature = seed_production_skill()
    tampered = hashlib.sha256(b"tampered-bundle").hexdigest()
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE skill_bundles SET bundle_digest=%s WHERE skill_name=%s AND version=%s", (tampered, name, version))
    denied = httpx.post(f"{API}/v1/skills/{name}/{version}/authorize-execution", headers=HEADERS, timeout=15)
    assert denied.status_code != 200
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE skill_bundles SET bundle_digest=%s, signature=%s WHERE skill_name=%s AND version=%s", (original, signature, name, version))
