from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.adapters.meta import MetaConfig, MetaReelsAdapter
from app.models import ActionClass, ExternalActionIntent


def emit(gate: str, status: str, evidence: dict) -> None:
    payload = {"gate": gate, "status": status, "evidence": evidence, "recorded_at": datetime.now(timezone.utc).isoformat()}
    payload["evidence_sha256"] = hashlib.sha256(json.dumps(payload["evidence"], sort_keys=True).encode()).hexdigest()
    print(json.dumps(payload, sort_keys=True))


async def meta_test() -> None:
    token = os.environ.get("META_TEST_ACCESS_TOKEN", "")
    user_id = os.environ.get("META_TEST_IG_USER_ID", "")
    graph_version = os.environ.get("META_GRAPH_VERSION", "")
    video_url = os.environ.get("META_TEST_VIDEO_URL", "")
    if not all((token, user_id, graph_version, video_url)):
        emit("meta_test_e2e", "NOT_RUN", {"reason": "missing_test_credentials_or_video"})
        return
    adapter = MetaReelsAdapter(MetaConfig(token, user_id, graph_version))
    if not await adapter.validate_session():
        emit("meta_test_e2e", "FAIL", {"reason": "session_validation_failed"})
        return
    intent = ExternalActionIntent(
        idempotency_key=f"p0c-meta-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        action_class=ActionClass.PUBLISH_REEL,
        target="meta_test",
        payload={"video_url": video_url, "caption": "P0-C qualification TEST content"},
        approved=True,
    )
    media_id = await adapter.execute(intent)
    status = await adapter.get_status(media_id)
    emit("meta_test_e2e", "PASS" if status == "CONFIRMED" else "FAIL", {"media_id": media_id, "status": status})


async def stripe_test() -> None:
    key = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
    endpoint = os.environ.get("STRIPE_TEST_EVIDENCE_ENDPOINT", "")
    if not key:
        emit("stripe_test_e2e", "NOT_RUN", {"reason": "missing_test_secret_key"})
        return
    if not key.startswith("sk_test_"):
        emit("stripe_test_e2e", "FAIL", {"reason": "non_test_key_rejected"})
        return
    async with httpx.AsyncClient(timeout=15.0, auth=(key, ""), base_url="https://api.stripe.com") as stripe:
        account = await stripe.get("/v1/account")
        account.raise_for_status()
        if account.json().get("livemode") is True:
            emit("stripe_test_e2e", "FAIL", {"reason": "livemode_account_rejected"})
            return
    if not endpoint:
        emit("stripe_test_e2e", "NOT_RUN", {"reason": "test_account_verified_but_evidence_endpoint_missing"})
        return
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        emit("stripe_test_e2e", "FAIL", {"reason": "https_evidence_endpoint_required"})
        return
    async with httpx.AsyncClient(timeout=15.0) as evidence_client:
        evidence = await evidence_client.get(endpoint)
        evidence.raise_for_status()
    body = evidence.json()
    required = {"signed_webhook_verified", "receipt_deduplicated", "fulfillment_idempotent", "settlement_reconciled"}
    passed = all(body.get(name) is True for name in required)
    emit("stripe_test_e2e", "PASS" if passed else "FAIL", {name: bool(body.get(name)) for name in sorted(required)})


async def main() -> None:
    await meta_test()
    await stripe_test()


if __name__ == "__main__":
    asyncio.run(main())
