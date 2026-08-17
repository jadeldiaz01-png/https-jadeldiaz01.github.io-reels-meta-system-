import pytest

from app.models import ActionClass, ExternalActionIntent, IntentState
from app.orchestrator import Orchestrator
from app.policy import PolicyEngine


def intent(action: ActionClass, **payload):
    return ExternalActionIntent(
        idempotency_key=f"test:{action}", action_class=action, target="sandbox", payload=payload
    )


def test_external_write_fails_closed_by_default():
    decision = PolicyEngine().evaluate(intent(ActionClass.PUBLISH_REEL))
    assert not decision.allowed
    assert "external_execution_disabled" in decision.reasons


def test_price_change_requires_human_approval():
    decision = PolicyEngine(external_execution_enabled=True).evaluate(intent(ActionClass.CHANGE_PRICE))
    assert not decision.allowed
    assert decision.approval_required


@pytest.mark.asyncio
async def test_timeout_becomes_unknown_then_reconciles():
    flow = Orchestrator(PolicyEngine(external_execution_enabled=True))
    item = intent(ActionClass.PUBLISH_REEL, copyright_status="verified")

    async def timeout_executor(_):
        raise TimeoutError

    item = await flow.execute(item, timeout_executor)
    assert item.state == IntentState.UNKNOWN

    async def reconciler(_):
        return "ig_media_123"

    item = await flow.reconcile(item, reconciler)
    assert item.state == IntentState.CONFIRMED
    assert item.external_id == "ig_media_123"
