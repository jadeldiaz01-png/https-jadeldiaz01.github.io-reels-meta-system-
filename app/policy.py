from __future__ import annotations

from app.models import ActionClass, ExternalActionIntent, PolicyDecision


ALWAYS_HUMAN = {
    ActionClass.CREATE_OFFER,
    ActionClass.CHANGE_PRICE,
}

EXTERNAL_WRITES = {
    ActionClass.PUBLISH_REEL,
    ActionClass.CREATE_OFFER,
    ActionClass.FULFILL_ORDER,
    ActionClass.CUSTOMER_MESSAGE,
    ActionClass.CHANGE_PRICE,
}


class PolicyEngine:
    def __init__(self, *, external_execution_enabled: bool = False) -> None:
        self.external_execution_enabled = external_execution_enabled

    def evaluate(self, intent: ExternalActionIntent) -> PolicyDecision:
        reasons: list[str] = []

        if not intent.idempotency_key.strip():
            return PolicyDecision(allowed=False, reasons=["missing_idempotency_key"])

        if intent.action_class in ALWAYS_HUMAN and not intent.approved:
            return PolicyDecision(
                allowed=False,
                approval_required=True,
                reasons=["human_approval_required"],
            )

        if intent.action_class in EXTERNAL_WRITES and not self.external_execution_enabled:
            reasons.append("external_execution_disabled")

        if intent.payload.get("requires_captcha_bypass"):
            reasons.append("captcha_bypass_forbidden")
        if intent.payload.get("impersonation"):
            reasons.append("impersonation_forbidden")
        if intent.payload.get("fake_engagement"):
            reasons.append("fake_engagement_forbidden")
        if intent.payload.get("copyright_status") == "unverified":
            reasons.append("copyright_not_verified")

        return PolicyDecision(allowed=not reasons, reasons=reasons)
