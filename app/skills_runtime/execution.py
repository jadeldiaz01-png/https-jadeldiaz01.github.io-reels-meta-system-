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
    """Fail-closed authorization gate evaluated immediately before skill execution."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        registry: PostgresSkillRegistry,
        controls: PostgresRuntimeControls,
        signer: OpenBaoTransitSigner,
        policy: OpaSkillPolicyClient,
    ) -> None:
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
                SELECT bundle_digest, signature, signer_key
                FROM skill_bundles
                WHERE skill_name=:name AND version=:version
                ORDER BY created_at DESC LIMIT 1
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
        })
        if not bool(decision.get("allow")):
            raise PermissionError("execution_policy_denied")

        execution_id = uuid4()
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO skill_execution_leases(execution_id,skill_name,version,bundle_digest,status)
                VALUES (:id,:name,:version,:digest,'AUTHORIZED')
            """), {"id": execution_id, "name": name, "version": version, "digest": bundle["bundle_digest"]})
        return execution_id
