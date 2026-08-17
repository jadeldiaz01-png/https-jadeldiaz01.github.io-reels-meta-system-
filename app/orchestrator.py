from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.models import ExternalActionIntent, IntentState
from app.policy import PolicyEngine

Executor = Callable[[ExternalActionIntent], Awaitable[str]]
Reconciler = Callable[[ExternalActionIntent], Awaitable[str | None]]


class Orchestrator:
    def __init__(self, policy: PolicyEngine) -> None:
        self.policy = policy

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
