from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.models import ExternalActionIntent, IntentState
from app.policy import PolicyEngine
from app.skills_runtime.models import SkillRecord, SkillStage
from app.skills_runtime.service import SkillRuntimeService

Executor = Callable[[ExternalActionIntent], Awaitable[str]]
Reconciler = Callable[[ExternalActionIntent], Awaitable[str | None]]


class Orchestrator:
    def __init__(self, policy: PolicyEngine, *, skill_runtime: SkillRuntimeService | None = None) -> None:
        self.policy = policy
        self.skill_runtime = skill_runtime

    async def execute(self, intent: ExternalActionIntent, executor: Executor) -> ExternalActionIntent:
        decision = self.policy.evaluate(intent)
        intent.evidence.append({"type": "policy_decision", "decision": decision.model_dump()})

        if decision.approval_required:
            intent.state = IntentState.WAITING_APPROVAL
            return intent
        if not decision.allowed:
            intent.state = IntentState.REJECTED
            return intent

        intent.state = IntentState.AUTHORIZED
        intent.attempt += 1
        intent.state = IntentState.DISPATCHING
        try:
            external_id = await executor(intent)
        except TimeoutError:
            intent.state = IntentState.UNKNOWN
            intent.evidence.append({"type": "dispatch_timeout"})
            return intent
        except Exception as exc:
            intent.state = IntentState.FAILED_FINAL
            intent.evidence.append({"type": "dispatch_failure", "error": type(exc).__name__})
            return intent

        intent.external_id = external_id
        intent.state = IntentState.DISPATCHED
        return intent

    async def reconcile(self, intent: ExternalActionIntent, reconciler: Reconciler) -> ExternalActionIntent:
        if intent.state not in {IntentState.UNKNOWN, IntentState.DISPATCHED}:
            return intent
        intent.state = IntentState.RECONCILING
        external_id = await reconciler(intent)
        if external_id:
            intent.external_id = external_id
            intent.state = IntentState.CONFIRMED
            intent.evidence.append({"type": "reconciled", "external_id": external_id})
        else:
            intent.state = IntentState.UNKNOWN
        return intent

    async def promote_skill(self, record: SkillRecord, target: SkillStage) -> SkillRecord:
        if self.skill_runtime is None:
            raise RuntimeError("skills_runtime_not_configured")
        return await self.skill_runtime.promote(record, target)
