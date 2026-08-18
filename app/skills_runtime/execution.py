from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.skills_runtime.controls import PostgresRuntimeControls
from app.skills_runtime.models import SkillStage
from app.skills_runtime.openbao import OpenBaoTransitSigner
from app.skills_runtime.opa import OpaSkillPolicyClient
from app.skills_runtime.registry import PostgresSkillRegistry


class SkillExecutionAuthorizer:
    """Fail-closed authorization and lease guard evaluated before every external side effect."""

    def __init__(self, *, engine: AsyncEngine, registry: PostgresSkillRegistry, controls: PostgresRuntimeControls, signer: OpenBaoTransitSigner, policy: OpaSkillPolicyClient) -> None:
        self.engine = engine
        self.registry = registry
        self.controls = controls
        self.signer = signer
        self.policy = policy

    async def authorize(self, *, name: str, version: str) -> UUID:
        record = await self.registry.get(name, version)
        if record.stage != SkillStage.PRODUCTION:
            raise PermissionError("skill_not_production")
        control = await self.controls.get(name, version)
        if not control.enabled:
            raise PermissionError("skill_kill_switch_disabled")
        if control.revoked:
            raise PermissionError("skill_revoked")
        async with self.engine.connect() as conn:
            bundle = (await conn.execute(text("""
                SELECT bundle_digest, signature, signer_key FROM skill_bundles
                WHERE skill_name=:name AND version=:version ORDER BY created_at DESC LIMIT 1
            """), {"name": name, "version": version})).mappings().one_or_none()
        if bundle is None:
            raise PermissionError("signed_bundle_missing")
        if not await self.signer.verify_digest(bundle["bundle_digest"], bundle["signature"], key_name=bundle["signer_key"]):
            raise PermissionError("bundle_signature_invalid")
        decision = await self.policy.evaluate({
            "operation": "EXECUTE",
            "identity": record.identity.model_dump(),
            "stage": record.stage.value,
            "control": {"enabled": control.enabled, "revoked": control.revoked},
            "bundle": {"digest": bundle["bundle_digest"], "signature_verified": True},
        }, decision="execution")
        if not bool(decision.get("allow")):
            raise PermissionError("execution_policy_denied")
        execution_id = uuid4()
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO skill_execution_leases(execution_id,skill_name,version,bundle_digest,status)
                VALUES (:id,:name,:version,:digest,'AUTHORIZED')
            """), {"id": execution_id, "name": name, "version": version, "digest": bundle["bundle_digest"]})
        return execution_id

    async def assert_active(self, execution_id: UUID) -> None:
        async with self.engine.connect() as conn:
            row = (await conn.execute(text("""
                SELECT skill_name, version, status FROM skill_execution_leases WHERE execution_id=:id
            """), {"id": execution_id})).mappings().one_or_none()
        if row is None or row["status"] not in {"AUTHORIZED", "RUNNING"}:
            raise PermissionError("execution_lease_not_active")
        control = await self.controls.get(row["skill_name"], row["version"])
        if not control.enabled or control.revoked:
            raise PermissionError("execution_revoked_by_runtime_control")

    async def mark_running(self, execution_id: UUID) -> None:
        await self.assert_active(execution_id)
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                UPDATE skill_execution_leases SET status='RUNNING', updated_at=now()
                WHERE execution_id=:id AND status='AUTHORIZED'
            """), {"id": execution_id})
            if result.rowcount != 1:
                raise PermissionError("execution_lease_transition_denied")

    async def complete(self, execution_id: UUID, *, succeeded: bool) -> None:
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                UPDATE skill_execution_leases SET status=:status, updated_at=now()
                WHERE execution_id=:id AND status IN ('AUTHORIZED','RUNNING')
            """), {"id": execution_id, "status": "SUCCEEDED" if succeeded else "FAILED"})
            if result.rowcount != 1:
                raise PermissionError("execution_lease_not_completable")
