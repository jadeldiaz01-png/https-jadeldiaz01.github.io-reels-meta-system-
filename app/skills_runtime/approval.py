from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ApprovalRecord(BaseModel):
    id: int
    skill_name: str
    version: str
    requested_stage: str
    status: ApprovalStatus
    requested_by: str
    decided_by: str | None = None
    reason: str | None = None
    request_digest: str


def approval_digest(skill_name: str, version: str, target: str, evidence: dict[str, Any]) -> str:
    material = json.dumps({"skill_name": skill_name, "version": version, "target": target, "evidence": evidence}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode()).hexdigest()


class PostgresApprovalService:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def request(self, *, skill_name: str, version: str, requested_by: str, evidence: dict[str, Any]) -> ApprovalRecord:
        digest = approval_digest(skill_name, version, "PRODUCTION", evidence)
        async with self.engine.begin() as conn:
            row = (await conn.execute(text("""
                INSERT INTO skill_approvals(skill_name,version,requested_stage,status,requested_by,request_digest)
                VALUES (:name,:version,'PRODUCTION','PENDING',:requested_by,:digest)
                ON CONFLICT (skill_name,version,requested_stage,request_digest)
                DO UPDATE SET requested_by = EXCLUDED.requested_by
                RETURNING id,skill_name,version,requested_stage,status,requested_by,decided_by,reason,request_digest
            """), {"name": skill_name, "version": version, "requested_by": requested_by, "digest": digest})).mappings().one()
        return ApprovalRecord(**row)

    async def decide(self, *, approval_id: int, approved: bool, decided_by: str, reason: str) -> ApprovalRecord:
        if not decided_by.strip():
            raise ValueError("decided_by_required")
        status = "APPROVED" if approved else "REJECTED"
        async with self.engine.begin() as conn:
            row = (await conn.execute(text("""
                UPDATE skill_approvals
                SET status=:status, decided_by=:decided_by, reason=:reason, decided_at=:decided_at
                WHERE id=:id AND status='PENDING'
                RETURNING id,skill_name,version,requested_stage,status,requested_by,decided_by,reason,request_digest
            """), {"id": approval_id, "status": status, "decided_by": decided_by, "reason": reason, "decided_at": datetime.now(UTC)})).mappings().one_or_none()
        if row is None:
            raise ValueError("approval_not_pending_or_missing")
        return ApprovalRecord(**row)

    async def approved_for(self, *, skill_name: str, version: str) -> bool:
        async with self.engine.connect() as conn:
            value = await conn.scalar(text("""
                SELECT EXISTS(
                    SELECT 1 FROM skill_approvals
                    WHERE skill_name=:name AND version=:version AND requested_stage='PRODUCTION' AND status='APPROVED'
                )
            """), {"name": skill_name, "version": version})
        return bool(value)
