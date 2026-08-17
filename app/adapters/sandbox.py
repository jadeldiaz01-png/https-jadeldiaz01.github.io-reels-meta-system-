from __future__ import annotations

import hashlib
from app.adapters.base import PlatformAdapter
from app.models import ExternalActionIntent


class SandboxAdapter(PlatformAdapter):
    """Deterministic adapter for TEST/SANDBOX only; never performs an external write."""

    def __init__(self) -> None:
        self.by_key: dict[str, str] = {}
        self.status: dict[str, str] = {}

    async def validate_session(self) -> bool:
        return True

    async def check_capabilities(self) -> set[str]:
        return {"publish_reel", "fulfill_order", "reconcile", "idempotency"}

    async def prepare_action(self, intent: ExternalActionIntent) -> dict:
        return {"idempotency_key": intent.idempotency_key, "target": "sandbox", "payload": intent.payload}

    async def execute(self, intent: ExternalActionIntent) -> str:
        if intent.idempotency_key in self.by_key:
            return self.by_key[intent.idempotency_key]
        external_id = "sbx_" + hashlib.sha256(intent.idempotency_key.encode()).hexdigest()[:20]
        self.by_key[intent.idempotency_key] = external_id
        self.status[external_id] = "CONFIRMED"
        if intent.payload.get("simulate_lost_response"):
            raise TimeoutError("sandbox lost response after commit")
        return external_id

    async def get_status(self, external_id: str) -> str:
        return self.status.get(external_id, "UNKNOWN")

    async def reconcile(self, intent: ExternalActionIntent) -> str | None:
        return self.by_key.get(intent.idempotency_key)

    async def cancel(self, external_id: str) -> bool:
        if external_id not in self.status:
            return False
        self.status[external_id] = "CANCELLED"
        return True

    async def healthcheck(self) -> bool:
        return True
