from __future__ import annotations

from app.skills_runtime.models import PromotionDecision, SkillRecord, SkillStage


ORDER = [
    SkillStage.DRAFT,
    SkillStage.REVIEWED,
    SkillStage.TESTED,
    SkillStage.VALIDATED,
    SkillStage.PRODUCTION,
]


class SkillLifecycle:
    def evaluate(self, record: SkillRecord, target: SkillStage) -> PromotionDecision:
        current_idx = ORDER.index(record.stage)
        target_idx = ORDER.index(target)
        reasons: list[str] = []

        if target_idx != current_idx + 1:
            return PromotionDecision(
                allowed=False,
                from_stage=record.stage,
                to_stage=target,
                reasons=["non_sequential_transition"],
            )

        e = record.evidence
        if target is SkillStage.REVIEWED and not e.review_passed:
            reasons.append("review_evidence_missing")
        elif target is SkillStage.TESTED:
            if not e.tests_passed:
                reasons.append("tests_failed_or_missing")
            if not e.ci_run_id:
                reasons.append("ci_evidence_missing")
        elif target is SkillStage.VALIDATED:
            if not e.evals_passed:
                reasons.append("evals_failed_or_missing")
            if not e.security_passed:
                reasons.append("security_gate_failed_or_missing")
            if not e.policy_passed:
                reasons.append("policy_gate_failed_or_missing")
            if not e.signature_verified:
                reasons.append("signature_verification_missing")
        elif target is SkillStage.PRODUCTION:
            if not e.critical_human_approval:
                reasons.append("critical_human_approval_required")
            if not e.signature_verified:
                reasons.append("signature_verification_missing")
            return PromotionDecision(
                allowed=not reasons,
                from_stage=record.stage,
                to_stage=target,
                reasons=reasons,
                requires_human_approval=True,
            )

        return PromotionDecision(
            allowed=not reasons,
            from_stage=record.stage,
            to_stage=target,
            reasons=reasons,
            requires_human_approval=False,
        )

    def promote(self, record: SkillRecord, target: SkillStage) -> SkillRecord:
        decision = self.evaluate(record, target)
        if not decision.allowed:
            raise PermissionError(",".join(decision.reasons))
        record.stage = target
        record.revision += 1
        return record
