import pytest

from app.adapters.sandbox import SandboxAdapter
from app.models import ActionClass, ExternalActionIntent, IntentState
from app.orchestrator import Orchestrator
from app.policy import PolicyEngine


def make_intent(key: str, **payload):
    return ExternalActionIntent(idempotency_key=key, action_class=ActionClass.PUBLISH_REEL,
                                target="sandbox", payload={"copyright_status": "verified", **payload})


@pytest.mark.asyncio
async def test_duplicate_dispatch_is_idempotent():
    adapter = SandboxAdapter()
    a = make_intent("reel:42")
    b = make_intent("reel:42")
    first = await adapter.execute(a)
    second = await adapter.execute(b)
    assert first == second
    assert len(adapter.by_key) == 1


@pytest.mark.asyncio
async def test_lost_response_reconciles_without_duplicate_side_effect():
    adapter = SandboxAdapter()
    flow = Orchestrator(PolicyEngine(external_execution_enabled=True))
    item = make_intent("reel:lost-response", simulate_lost_response=True)
    item = await flow.execute(item, adapter.execute)
    assert item.state == IntentState.UNKNOWN
    assert len(adapter.by_key) == 1
    item = await flow.reconcile(item, adapter.reconcile)
    assert item.state == IntentState.CONFIRMED
    assert item.external_id == adapter.by_key[item.idempotency_key]
    assert len(adapter.by_key) == 1


def test_policy_denies_unverified_copyright():
    item = ExternalActionIntent(idempotency_key="reel:copyright", action_class=ActionClass.PUBLISH_REEL,
                                target="sandbox", payload={"copyright_status": "unverified"})
    decision = PolicyEngine(external_execution_enabled=True).evaluate(item)
    assert not decision.allowed
    assert "copyright_not_verified" in decision.reasons
