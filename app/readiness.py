from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

MANDATORY_LIVE_GATES = (
    "unit_and_integration_tests",
    "postgres_durability",
    "idempotency",
    "unknown_reconciliation",
    "opa_fail_closed",
    "openbao_production_identity",
    "evidence_ledger",
    "kill_switches",
    "opentelemetry",
    "meta_test_e2e",
    "stripe_test_e2e",
    "backup_restore_pitr",
    "chaos_restart_recovery",
    "signed_evidence_bundle",
    "human_go_live_approval",
)

@dataclass(frozen=True)
class ReadinessDecision:
    decision: str
    blockers: tuple[str, ...]


def evaluate_live_pilot(gates: Mapping[str, str], *, external_execution_enabled: bool) -> ReadinessDecision:
    blockers = tuple(gate for gate in MANDATORY_LIVE_GATES if gates.get(gate) != "PASS")
    if external_execution_enabled:
        blockers = blockers + ("external_execution_must_remain_disabled_during_qualification",)
    return ReadinessDecision("LIVE_PILOT_READY" if not blockers else "NO_GO", blockers)
