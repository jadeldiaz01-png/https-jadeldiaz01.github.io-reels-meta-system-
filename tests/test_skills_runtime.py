from __future__ import annotations

import pytest

from app.skills_runtime.agent_registry import AgentRegistration, AgentRegistry
from app.skills_runtime.lifecycle import SkillLifecycle
from app.skills_runtime.models import PromotionEvidence, SkillIdentity, SkillRecord, SkillStage


def record(stage: SkillStage, **evidence) -> SkillRecord:
    return SkillRecord(
        identity=SkillIdentity(name="example", version="1.0.0", digest="sha256:abc"),
        stage=stage,
        manifest={"self_promotion": False, "external_writes": False},
        evidence=PromotionEvidence(**evidence),
    )


def test_draft_to_reviewed_requires_review():
    lifecycle = SkillLifecycle()
    assert not lifecycle.evaluate(record(SkillStage.DRAFT), SkillStage.REVIEWED).allowed
    assert lifecycle.evaluate(record(SkillStage.DRAFT, review_passed=True), SkillStage.REVIEWED).allowed


def test_tested_requires_tests_and_ci():
    lifecycle = SkillLifecycle()
    denied = lifecycle.evaluate(record(SkillStage.REVIEWED, tests_passed=True), SkillStage.TESTED)
    assert not denied.allowed
    assert "ci_evidence_missing" in denied.reasons


def test_validated_requires_full_machine_evidence():
    lifecycle = SkillLifecycle()
    allowed = lifecycle.evaluate(
        record(
            SkillStage.TESTED,
            evals_passed=True,
            security_passed=True,
            policy_passed=True,
            signature_verified=True,
        ),
        SkillStage.VALIDATED,
    )
    assert allowed.allowed


def test_production_requires_human_approval():
    lifecycle = SkillLifecycle()
    denied = lifecycle.evaluate(
        record(SkillStage.VALIDATED, signature_verified=True),
        SkillStage.PRODUCTION,
    )
    assert not denied.allowed
    assert denied.requires_human_approval
    assert "critical_human_approval_required" in denied.reasons

    allowed = lifecycle.evaluate(
        record(SkillStage.VALIDATED, signature_verified=True, critical_human_approval=True),
        SkillStage.PRODUCTION,
    )
    assert allowed.allowed
    assert allowed.requires_human_approval


def test_non_sequential_promotion_is_forbidden():
    lifecycle = SkillLifecycle()
    decision = lifecycle.evaluate(record(SkillStage.DRAFT, tests_passed=True), SkillStage.TESTED)
    assert not decision.allowed
    assert decision.reasons == ["non_sequential_transition"]


def test_agent_registry_forbids_agent_production_approval():
    registry = AgentRegistry([
        AgentRegistration(name="safe", version="1", may_approve_production=False),
    ])
    registry.assert_no_self_approval()

    unsafe = AgentRegistry([
        AgentRegistration(name="unsafe", version="1", may_approve_production=True),
    ])
    with pytest.raises(ValueError, match="agent_production_approval_forbidden"):
        unsafe.assert_no_self_approval()
