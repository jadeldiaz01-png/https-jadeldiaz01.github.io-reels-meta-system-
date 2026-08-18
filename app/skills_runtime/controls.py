from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True)
class RuntimeControl:
    enabled: bool
    revoked: bool
    reason: str | None


class PostgresRuntimeControls:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def get(self, name: str, version: str) -> RuntimeControl:
        async with self.engine.connect() as conn:
            row = (await conn.execute(text("""
                SELECT enabled, revoked, reason FROM skill_runtime_controls
                WHERE skill_name=:name AND version=:version
            """), {"name": name, "version": version})).mappings().one_or_none()
        if row is None:
            return RuntimeControl(enabled=False, revoked=False, reason="control_record_missing_fail_closed")
        return RuntimeControl(enabled=bool(row["enabled"]), revoked=bool(row["revoked"]), reason=row["reason"])

    async def set_enabled(self, *, name: str, version: str, enabled: bool, actor: str, reason: str) -> RuntimeControl:
        if not actor.strip() or not reason.strip():
            raise ValueError("actor_and_reason_required")
        async with self.engine.begin() as conn:
            row = (await conn.execute(text("""
                INSERT INTO skill_runtime_controls(skill_name,version,enabled,revoked,reason,updated_by)
                VALUES (:name,:version,:enabled,FALSE,:reason,:actor)
                ON CONFLICT (skill_name,version) DO UPDATE
                SET enabled=EXCLUDED.enabled, reason=EXCLUDED.reason, updated_by=EXCLUDED.updated_by, updated_at=now()
                RETURNING enabled,revoked,reason
            """), {"name": name, "version": version, "enabled": enabled, "reason": reason, "actor": actor})).mappings().one()
        return RuntimeControl(bool(row["enabled"]), bool(row["revoked"]), row["reason"])

    async def revoke(self, *, name: str, version: str, actor: str, reason: str) -> RuntimeControl:
        if not actor.strip() or not reason.strip():
            raise ValueError("actor_and_reason_required")
        async with self.engine.begin() as conn:
            row = (await conn.execute(text("""
                INSERT INTO skill_runtime_controls(skill_name,version,enabled,revoked,reason,updated_by)
                VALUES (:name,:version,FALSE,TRUE,:reason,:actor)
                ON CONFLICT (skill_name,version) DO UPDATE
                SET enabled=FALSE, revoked=TRUE, reason=EXCLUDED.reason, updated_by=EXCLUDED.updated_by, updated_at=now()
                RETURNING enabled,revoked,reason
            """), {"name": name, "version": version, "reason": reason, "actor": actor})).mappings().one()
        return RuntimeControl(bool(row["enabled"]), bool(row["revoked"]), row["reason"])

    async def rollback(self, *, name: str, from_version: str, to_version: str, actor: str, reason: str) -> None:
        if from_version == to_version:
            raise ValueError("rollback_versions_must_differ")
        if not actor.strip() or not reason.strip():
            raise ValueError("actor_and_reason_required")
        async with self.engine.begin() as conn:
            target = (await conn.execute(text("""
                SELECT r.stage, COALESCE(c.revoked, FALSE) AS revoked
                FROM skill_registry r
                LEFT JOIN skill_runtime_controls c ON c.skill_name=r.name AND c.version=r.version
                WHERE r.name=:name AND r.version=:version
                FOR UPDATE OF r
            """), {"name": name, "version": to_version})).mappings().one_or_none()
            if target is None or target["stage"] != "PRODUCTION" or bool(target["revoked"]):
                raise ValueError("rollback_target_not_eligible")
            await conn.execute(text("""
                INSERT INTO skill_runtime_controls(skill_name,version,enabled,revoked,reason,updated_by)
                VALUES (:name,:from_version,FALSE,FALSE,:reason,:actor)
                ON CONFLICT (skill_name,version) DO UPDATE
                SET enabled=FALSE, reason=EXCLUDED.reason, updated_by=EXCLUDED.updated_by, updated_at=now()
            """), {"name": name, "from_version": from_version, "reason": f"rollback_from:{reason}", "actor": actor})
            await conn.execute(text("""
                INSERT INTO skill_runtime_controls(skill_name,version,enabled,revoked,reason,updated_by)
                VALUES (:name,:to_version,TRUE,FALSE,:reason,:actor)
                ON CONFLICT (skill_name,version) DO UPDATE
                SET enabled=TRUE, reason=EXCLUDED.reason, updated_by=EXCLUDED.updated_by, updated_at=now()
                WHERE skill_runtime_controls.revoked=FALSE
            """), {"name": name, "to_version": to_version, "reason": f"rollback_to:{reason}", "actor": actor})
