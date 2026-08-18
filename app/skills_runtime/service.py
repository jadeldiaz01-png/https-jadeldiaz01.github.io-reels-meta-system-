from __future__ import annotations

from typing import Protocol

from app.skills_runtime.lifecycle import SkillLifecycle
from app.skills_runtime.models import SkillRecord, SkillStage
from app.skills_runtime.opa import OpaSkillPolicyClient
from app.skills_runtime.registry import SkillRegistry


class EvidenceSink(Protocol):
    async def append(self, *, skill_name: str, version: str, event_type: str, payload: dict) -> str: ...


class SkillRuntimeService:
    def __init__(
        self,
        *,
        registry: SkillRegistry,
        lifecycle: SkillLifecycle,
        policy: OpaSkillPolicyClient,
        evidence: EvidenceSink,
    ) -> None:
        self.registry = registry
        self.lifecycle = lifecycle
        self.policy = policy
        self.evidence = evidence

    async def promote(self, record: SkillRecord, target: SkillStage) -> SkillRecord:
        local = self.lifecycle.evaluate(record, target)
        if not local.allowed:
            await self.evidence.append(
                skill_name=record.identity.name,
                version=record.identity.version,
                event_type="promotion_denied_local",
                payload=local.model_dump(mode="json"),
            )
            raise PermissionError(",".join(local.reasons))

        policy_input = {
            "from": record.stage.value,
            "to": target.value,
            "identity": record.identity.model_dump(),
            "manifest": record.manifest,
            "evidence": record.evidence.model_dump(),
        }
        decision = await self.policy.evaluate(policy_input)
        if not bool(decision.get("allow")):
            await self.evidence.append(
                skill_name=record.identity.name,
                version=record.identity.version,
                event_type="promotion_denied_policy",
                payload={"target": target.value, "decision": decision},
            )
            raise PermissionError("opa_policy_denied")

        promoted = self.lifecycle.promote(record, target)
        self.registry.register(promoted)
        await self.evidence.append(
            skill_name=promoted.identity.name,
            version=promoted.identity.version,
            event_type="skill_promoted",
            payload={
                "stage": promoted.stage.value,
                "revision": promoted.revision,
                "digest": promoted.identity.digest,
                "ci_run_id": promoted.evidence.ci_run_id,
            },
        )
        return promoted
