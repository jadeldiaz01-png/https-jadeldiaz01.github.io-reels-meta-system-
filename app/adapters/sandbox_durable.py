from __future__ import annotations

import hashlib

from sqlalchemy import create_engine, text

from app.adapters.base import PlatformAdapter
from app.models import ExternalActionIntent


class DurableSandboxAdapter(PlatformAdapter):
    """TEST/SANDBOX adapter whose effects survive process restart."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    async def validate_session(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def check_capabilities(self) -> set[str]:
        return {"publish_reel", "fulfill_order", "reconcile", "idempotency", "restart_recovery"}

    async def prepare_action(self, intent: ExternalActionIntent) -> dict:
        return {"idempotency_key": intent.idempotency_key, "target": "sandbox", "payload": intent.payload}

    async def execute(self, intent: ExternalActionIntent) -> str:
        external_id = "sbx_" + hashlib.sha256(intent.idempotency_key.encode()).hexdigest()[:20]
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT external_id FROM sandbox_effects WHERE idempotency_key=:key"), {"key": intent.idempotency_key}).first()
            if row:
                return str(row[0])
            conn.execute(text("""
                INSERT INTO sandbox_effects(idempotency_key,external_id,status,payload)
                VALUES (:key,:external_id,'CONFIRMED',CAST(:payload AS jsonb))
            """), {"key": intent.idempotency_key, "external_id": external_id, "payload": __import__('json').dumps(intent.payload)})
        if intent.payload.get("simulate_lost_response"):
            raise TimeoutError("sandbox lost response after durable commit")
        return external_id

    async def get_status(self, external_id: str) -> str:
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT status FROM sandbox_effects WHERE external_id=:id"), {"id": external_id}).first()
            return str(row[0]) if row else "UNKNOWN"

    async def reconcile(self, intent: ExternalActionIntent) -> str | None:
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT external_id FROM sandbox_effects WHERE idempotency_key=:key"), {"key": intent.idempotency_key}).first()
            return str(row[0]) if row else None

    async def cancel(self, external_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(text("UPDATE sandbox_effects SET status='CANCELLED',updated_at=now() WHERE external_id=:id"), {"id": external_id})
            return bool(result.rowcount)

    async def healthcheck(self) -> bool:
        return await self.validate_session()
