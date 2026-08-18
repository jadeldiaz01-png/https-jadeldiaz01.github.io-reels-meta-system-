from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class PostgresEvidenceLedger:
    """Append-only, hash-chained evidence records for skill lifecycle decisions."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def append(self, *, skill_name: str, version: str, event_type: str, payload: dict[str, Any]) -> str:
        async with self.engine.begin() as conn:
            previous = await conn.execute(
                text("SELECT entry_hash FROM skill_evidence_ledger ORDER BY id DESC LIMIT 1 FOR SHARE")
            )
            prev_hash = previous.scalar_one_or_none() or "GENESIS"
            occurred_at = datetime.now(UTC).isoformat()
            material = canonical_json({
                "skill_name": skill_name,
                "version": version,
                "event_type": event_type,
                "payload": payload,
                "previous_hash": prev_hash,
                "occurred_at": occurred_at,
            })
            entry_hash = hashlib.sha256(material.encode()).hexdigest()
            await conn.execute(
                text("""
                    INSERT INTO skill_evidence_ledger
                    (skill_name, version, event_type, payload, previous_hash, entry_hash, occurred_at)
                    VALUES (:skill_name, :version, :event_type, CAST(:payload AS jsonb), :previous_hash, :entry_hash, :occurred_at)
                """),
                {
                    "skill_name": skill_name,
                    "version": version,
                    "event_type": event_type,
                    "payload": canonical_json(payload),
                    "previous_hash": prev_hash,
                    "entry_hash": entry_hash,
                    "occurred_at": occurred_at,
                },
            )
            return entry_hash
