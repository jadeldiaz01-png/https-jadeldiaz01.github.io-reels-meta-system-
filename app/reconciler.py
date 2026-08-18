from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Mapping
from uuid import UUID

from sqlalchemy import create_engine, text

from app.adapters.base import PlatformAdapter
from app.models import ActionClass, ExternalActionIntent, IntentState


class DurableReconciler:
    """Claims ambiguous intents with PostgreSQL leases and reconciles them after crashes/restarts."""

    def __init__(self, database_url: str, adapters: Mapping[str, PlatformAdapter], *, worker_id: str, lease_seconds: int = 30) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.adapters = adapters
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds

    def claim_one(self) -> ExternalActionIntent | None:
        with self.engine.begin() as conn:
            row = conn.execute(text("""
                SELECT * FROM external_action_intents
                WHERE state IN ('UNKNOWN','DISPATCHED','RECONCILING')
                  AND (lease_expires_at IS NULL OR lease_expires_at < now())
                ORDER BY updated_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """)).mappings().first()
            if row is None:
                return None
            conn.execute(text("""
                UPDATE external_action_intents
                SET state='RECONCILING', lease_owner=:worker,
                    lease_expires_at=now() + (:lease_seconds * interval '1 second'), updated_at=now()
                WHERE id=:id
            """), {"worker": self.worker_id, "lease_seconds": self.lease_seconds, "id": row["id"]})
            return ExternalActionIntent(
                id=row["id"], idempotency_key=row["idempotency_key"], action_class=ActionClass(row["action_class"]),
                target=row["target"], payload=row["payload"], state=IntentState.RECONCILING,
                approved=row["approved"], external_id=row["external_id"], attempt=row["attempt"],
            )

    async def reconcile_one(self) -> bool:
        intent = self.claim_one()
        if intent is None:
            return False
        adapter = self.adapters.get(intent.target)
        if adapter is None:
            self._finish(intent.id, "UNKNOWN", None)
            return True
        try:
            external_id = await adapter.reconcile(intent)
        except Exception:
            self._finish(intent.id, "UNKNOWN", None)
            return True
        self._finish(intent.id, "CONFIRMED" if external_id else "UNKNOWN", external_id)
        return True

    def _finish(self, intent_id: UUID, state: str, external_id: str | None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("""
                UPDATE external_action_intents
                SET state=:state, external_id=COALESCE(:external_id,external_id),
                    lease_owner=NULL, lease_expires_at=NULL, updated_at=now()
                WHERE id=:id AND lease_owner=:worker
            """), {"state": state, "external_id": external_id, "id": intent_id, "worker": self.worker_id})

    async def run(self, *, poll_seconds: float = 1.0) -> None:
        while True:
            worked = await self.reconcile_one()
            if not worked:
                await asyncio.sleep(poll_seconds)
