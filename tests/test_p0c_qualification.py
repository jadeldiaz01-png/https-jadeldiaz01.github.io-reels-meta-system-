import os

import pytest
from sqlalchemy import create_engine, text

from app.adapters.sandbox_durable import DurableSandboxAdapter
from app.kill_switch import KillSwitchStore
from app.models import ActionClass, ExternalActionIntent, IntentState
from app.persistence import IntentRepository
from app.readiness import MANDATORY_LIVE_GATES, evaluate_live_pilot
from app.reconciler import DurableReconciler

DB = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB, reason="DATABASE_URL required")


def make_intent(key: str, **payload):
    return ExternalActionIntent(idempotency_key=key, action_class=ActionClass.PUBLISH_REEL, target="sandbox", payload=payload)


def test_db_kill_switch_hierarchy():
    store = KillSwitchStore(DB)
    item = make_intent("kill-test", account_id="acct-test")
    store.set("platform", "sandbox", enabled=True, reason="qualification", actor="pytest")
    assert store.evaluate(item).blocked
    store.set("platform", "sandbox", enabled=False, reason="reset", actor="pytest")
    assert not store.evaluate(item).blocked


@pytest.mark.asyncio
async def test_lost_response_survives_adapter_and_worker_restart():
    repo = IntentRepository(DB)
    first = DurableSandboxAdapter(DB)
    item = make_intent("restart-recovery", simulate_lost_response=True)
    item.state = IntentState.UNKNOWN
    repo.save(item)
    with pytest.raises(TimeoutError):
        await first.execute(item)

    restarted_adapter = DurableSandboxAdapter(DB)
    worker = DurableReconciler(DB, {"sandbox": restarted_adapter}, worker_id="pytest-restarted")
    assert await worker.reconcile_one()
    restored = repo.get_by_key("restart-recovery")
    assert restored is not None
    assert restored.state == IntentState.CONFIRMED
    assert restored.external_id and restored.external_id.startswith("sbx_")


def test_readiness_fails_closed_then_passes_only_all_gates():
    decision = evaluate_live_pilot({}, external_execution_enabled=False)
    assert decision.decision == "NO_GO"
    gates = {gate: "PASS" for gate in MANDATORY_LIVE_GATES}
    assert evaluate_live_pilot(gates, external_execution_enabled=False).decision == "LIVE_PILOT_READY"
    assert evaluate_live_pilot(gates, external_execution_enabled=True).decision == "NO_GO"
