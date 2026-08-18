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
CI = {"X-Authenticated-Subject": "e2e-ci", "X-Actor-Type": "service"}
REQUESTER = {"X-Authenticated-Subject": "e2e-requester", "X-Actor-Type": "service"}
APPROVER = {"X-Authenticated-Subject": "e2e-approver", "X-Actor-Type": "human"}
HUMAN = {"X-Authenticated-Subject": "e2e-human", "X-Actor-Type": "human"}


def canonical_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def transit_sign(digest_hex: str) -> str:
    assert BAO_TOKEN, "BAO_DEV_ROOT_TOKEN required"
    payload = {"input": base64.b64encode(bytes.fromhex(digest_hex)).decode(), "prehashed": True}
    response = httpx.post(f"{BAO}/v1/transit/sign/skills-runtime/sha2-256", headers={"X-Vault-Token": BAO_TOKEN}, json=payload, timeout=5)
    response.raise_for_status()
    return response.json()["data"]["signature"]


def call(method: str, path: str, *, headers: dict, json_body: dict | None = None, expected: int = 200) -> httpx.Response:
    response = httpx.request(method, f"{API}{path}", headers=headers, json=json_body, timeout=15)
    assert response.status_code == expected, response.text
    return response


def full_pipeline(name: str = "e2e-skill", version: str = "1.0.0") -> tuple[str, str, str, str]:
    manifest = {"name": name, "version": version, "domain": "e2e", "self_promotion": False, "external_writes": False}
    call("POST", "/v1/skills", headers=CI, json_body={"name": name, "version": version, "manifest": manifest})

    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"review_passed": True, "artifacts": ["review:e2e"]})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "REVIEWED"})

    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"tests_passed": True, "ci_run_id": "e2e-ci-run"})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "TESTED"})

    bundle_digest = hashlib.sha256(f"{name}:{version}:immutable-bundle".encode()).hexdigest()
    signature = transit_sign(bundle_digest)
    call("POST", f"/v1/skills/{name}/{version}/bundles", headers=CI, json_body={
        "bundle_digest": bundle_digest,
        "manifest_digest": canonical_digest(manifest),
        "signature": signature,
        "signer_key": "skills-runtime",
    })
    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={
        "evals_passed": True,
        "security_passed": True,
        "policy_passed": True,
        "artifacts": ["eval:e2e", "security:e2e", "policy:e2e"],
    })
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "VALIDATED"})

    approval = call("POST", f"/v1/skills/{name}/{version}/approvals", headers=REQUESTER).json()
    call("POST", f"/v1/skills/approvals/{approval['id']}/decision", headers=APPROVER, json_body={"approved": True, "reason": "e2e-production-gate"})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=APPROVER, json_body={"target": "PRODUCTION"})
    return name, version, bundle_digest, signature


def test_complete_pipeline_reaches_production_and_authorizes_execution():
    name, version, _, _ = full_pipeline()
    record = call("GET", f"/v1/skills/{name}/{version}", headers=HUMAN).json()
    assert record["stage"] == "PRODUCTION"
    authorized = call("POST", f"/v1/skills/{name}/{version}/authorize-execution", headers=HUMAN).json()
    assert authorized["authorized"] is True
    assert authorized["execution_id"]


def test_kill_switch_invalidates_active_lease_and_blocks_new_execution():
    name, version, _, _ = full_pipeline("e2e-kill", "1.0.0")
    authorized = call("POST", f"/v1/skills/{name}/{version}/authorize-execution", headers=HUMAN).json()
    execution_id = authorized["execution_id"]
    call("PUT", f"/v1/skills/{name}/{version}/control", headers=CI, json_body={"enabled": False, "reason": "e2e-kill-switch"})
    denied = httpx.post(f"{API}/v1/skills/{name}/{version}/authorize-execution", headers=HUMAN, timeout=5)
    assert denied.status_code == 403
    assert "skill_kill_switch_disabled" in denied.text
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM skill_execution_leases WHERE execution_id=%s", (execution_id,))
            assert cur.fetchone()[0] == "REVOKED"
    call("PUT", f"/v1/skills/{name}/{version}/control", headers=HUMAN, json_body={"enabled": True, "reason": "e2e-human-restore"})


def test_tampered_bundle_signature_fails_closed():
    name, version, original, signature = full_pipeline("e2e-tamper", "1.0.0")
    tampered = hashlib.sha256(b"tampered-bundle").hexdigest()
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE skill_bundles SET bundle_digest=%s WHERE skill_name=%s AND version=%s", (tampered, name, version))
    denied = httpx.post(f"{API}/v1/skills/{name}/{version}/authorize-execution", headers=HUMAN, timeout=15)
    assert denied.status_code != 200
    with psycopg.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE skill_bundles SET bundle_digest=%s, signature=%s WHERE skill_name=%s AND version=%s", (original, signature, name, version))


def test_approval_becomes_invalid_if_snapshot_changes():
    name, version = "e2e-approval-binding", "1.0.0"
    manifest = {"name": name, "version": version, "domain": "e2e", "self_promotion": False, "external_writes": False}
    call("POST", "/v1/skills", headers=CI, json_body={"name": name, "version": version, "manifest": manifest})
    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"review_passed": True})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "REVIEWED"})
    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"tests_passed": True, "ci_run_id": "e2e-ci"})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "TESTED"})
    digest = hashlib.sha256(b"approval-binding-bundle").hexdigest()
    call("POST", f"/v1/skills/{name}/{version}/bundles", headers=CI, json_body={"bundle_digest": digest, "manifest_digest": canonical_digest(manifest), "signature": transit_sign(digest), "signer_key": "skills-runtime"})
    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"evals_passed": True, "security_passed": True, "policy_passed": True})
    call("POST", f"/v1/skills/{name}/{version}/promote", headers=CI, json_body={"target": "VALIDATED"})
    approval = call("POST", f"/v1/skills/{name}/{version}/approvals", headers=REQUESTER).json()
    call("POST", f"/v1/skills/approvals/{approval['id']}/decision", headers=APPROVER, json_body={"approved": True, "reason": "approved-before-change"})
    call("PUT", f"/v1/skills/{name}/{version}/evidence", headers=CI, json_body={"artifacts": ["late-change"]})
    denied = httpx.post(f"{API}/v1/skills/{name}/{version}/promote", headers=APPROVER, json={"target": "PRODUCTION"}, timeout=10)
    assert denied.status_code == 403
    assert "critical_human_approval_required" in denied.text
