import pytest

from app.models import ActionClass, ExternalActionIntent
from app.policy_opa import OpaPolicyClient


@pytest.mark.asyncio
async def test_opa_unavailable_denies_external_action():
    item = ExternalActionIntent(
        idempotency_key="opa:failclosed:1",
        action_class=ActionClass.PUBLISH_REEL,
        target="sandbox",
        payload={"copyright_status": "verified"},
    )
    decision = await OpaPolicyClient("http://127.0.0.1:9", timeout=0.05).evaluate(
        item, external_execution_enabled=True
    )
    assert not decision.allowed
    assert "opa_unavailable_fail_closed" in decision.reasons
