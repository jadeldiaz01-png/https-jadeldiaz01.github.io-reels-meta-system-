from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SkillStage(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    TESTED = "TESTED"
    VALIDATED = "VALIDATED"
    PRODUCTION = "PRODUCTION"


class SkillIdentity(BaseModel):
    name: str
    version: str
    digest: str


class PromotionEvidence(BaseModel):
    review_passed: bool = False
    tests_passed: bool = False
    evals_passed: bool = False
    security_passed: bool = False
    policy_passed: bool = False
    signature_verified: bool = False
    critical_human_approval: bool = False
    ci_run_id: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class SkillRecord(BaseModel):
    identity: SkillIdentity
    stage: SkillStage = SkillStage.DRAFT
    manifest: dict[str, Any]
    evidence: PromotionEvidence = Field(default_factory=PromotionEvidence)
    signature: str | None = None
    signer_key: str | None = None
    revision: int = 1


class PromotionDecision(BaseModel):
    allowed: bool
    from_stage: SkillStage
    to_stage: SkillStage
    reasons: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
