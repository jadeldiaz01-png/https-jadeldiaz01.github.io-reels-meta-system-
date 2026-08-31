import os
import pytest

from app.models import ActionClass, ExternalActionIntent, IntentState
from app.persistence import EvidenceLedger, IntentRepository

DB = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB, reason="DATABASE_URL not configured")


def test_intent_survives_repository_roundtrip_and_evidence_chains():
    repo = IntentRepository(DB)
    ledger = EvidenceLedger(DB)
    item = ExternalActionIntent(idempotency_key="ci:durable:1", action_class=ActionClass.PUBLISH_REEL,
                                target="sandbox", payload={"copyright_status": "verified"},
                                state=IntentState.UNKNOWN, attempt=1)
    repo.save(item)
    loaded = repo.get_by_key(item.idempotency_key)
    assert loaded is not None
    assert loaded.state == IntentState.UNKNOWN
    assert loaded.attempt == 1
    h1 = ledger.append("intent_unknown", {"key": item.idempotency_key}, item.id)
    h2 = ledger.append("reconciled", {"external_id": "sbx_ci"}, item.id)
    assert h1 != h2
    assert len(h1) == len(h2) == 64
