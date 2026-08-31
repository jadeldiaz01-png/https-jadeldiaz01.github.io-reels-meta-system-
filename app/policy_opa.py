from __future__ import annotations

import os
import httpx

from app.models import ExternalActionIntent, PolicyDecision


class OpaPolicyClient:
    """OPA Data API client. Network errors, malformed responses and missing decisions deny by default."""

    def __init__(self, base_url: str | None = None, *, timeout: float = 2.0) -> None:
        self.base_url = (base_url or os.getenv("OPA_URL", "http://127.0.0.1:8181")).rstrip("/")
        self.timeout = timeout

    async def evaluate(self, intent: ExternalActionIntent, *, external_execution_enabled: bool,
                       kill_switch: bool = False) -> PolicyDecision:
        body = {
            "input": {
                "idempotency_key": intent.idempotency_key,
                "action_class": intent.action_class.value,
                "approved": intent.approved,
                "payload": intent.payload,
                "external_execution_enabled": external_execution_enabled,
                "kill_switch": kill_switch,
            }
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/v1/data/revenue_engine/authz/decision", json=body)
                response.raise_for_status()
                data = response.json()
                result = data.get("result")
                if not isinstance(result, dict) or not isinstance(result.get("allowed"), bool):
                    return PolicyDecision(allowed=False, reasons=["opa_invalid_decision"])
                return PolicyDecision(
                    allowed=result["allowed"],
                    approval_required=bool(result.get("approval_required", False)),
                    reasons=[] if result["allowed"] else ["opa_denied"],
                )
        except (httpx.HTTPError, ValueError, TypeError):
            return PolicyDecision(allowed=False, reasons=["opa_unavailable_fail_closed"])
