from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.skills_runtime.approval import PostgresApprovalService
from app.skills_runtime.bundle_store import BundleAttestation, PostgresBundleStore, manifest_digest
from app.skills_runtime.controls import PostgresRuntimeControls
from app.skills_runtime.database import create_engine_from_env
from app.skills_runtime.evidence import PostgresEvidenceLedger
from app.skills_runtime.execution import SkillExecutionAuthorizer
from app.skills_runtime.lifecycle import SkillLifecycle
from app.skills_runtime.models import SkillIdentity, SkillRecord, SkillStage
from app.skills_runtime.opa import OpaSkillPolicyClient
from app.skills_runtime.openbao import OpenBaoTransitSigner
from app.skills_runtime.registry import PostgresSkillRegistry
from app.skills_runtime.service import SkillRuntimeService

router = APIRouter(prefix="/v1/skills", tags=["skills-runtime"])
engine = create_engine_from_env()
registry = PostgresSkillRegistry(engine)
controls = PostgresRuntimeControls(engine)
approvals = PostgresApprovalService(engine)
policy = OpaSkillPolicyClient()
signer = OpenBaoTransitSigner()
evidence = PostgresEvidenceLedger(engine)
runtime = SkillRuntimeService(registry=registry, lifecycle=SkillLifecycle(), policy=policy, evidence=evidence)
authorizer = SkillExecutionAuthorizer(engine=engine, registry=registry, controls=controls, signer=signer, policy=policy)
bundles = PostgresBundleStore(engine=engine, registry=registry, signer=signer, evidence=evidence)


class Actor(BaseModel):
    subject: str
    actor_type: str


def actor(
    x_authenticated_subject: Annotated[str | None, Header()] = None,
    x_actor_type: Annotated[str | None, Header()] = None,
) -> Actor:
    if os.getenv("TRUSTED_IDENTITY_PROXY", "false").lower() != "true":
        raise HTTPException(503, "trusted_identity_proxy_required")
    if not x_authenticated_subject or x_actor_type not in {"human", "service"}:
        raise HTTPException(401, "authenticated_actor_required")
    return Actor(subject=x_authenticated_subject, actor_type=x_actor_type)


def require_writer(who: Actor, env_name: str) -> None:
    allowed = {x.strip() for x in os.getenv(env_name, "").split(",") if x.strip()}
    if who.actor_type != "service" or who.subject not in allowed:
        raise HTTPException(403, f"writer_not_allowed:{env_name}")


def approval_snapshot(record: SkillRecord) -> dict:
    snapshot = record.model_dump(mode="json")
    snapshot["evidence"]["critical_human_approval"] = False
    return snapshot


class RegisterSkillRequest(BaseModel):
    name: str
    version: str
    manifest: dict


class EvidenceUpdate(BaseModel):
    review_passed: bool | None = None
    tests_passed: bool | None = None
    evals_passed: bool | None = None
    security_passed: bool | None = None
    policy_passed: bool | None = None
    ci_run_id: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class PromotionRequest(BaseModel):
    target: SkillStage


class ApprovalDecision(BaseModel):
    approved: bool
    reason: str


class ControlRequest(BaseModel):
    enabled: bool
    reason: str


class RevokeRequest(BaseModel):
    reason: str


class RollbackRequest(BaseModel):
    to_version: str
    reason: str


class BundleRequest(BaseModel):
    bundle_digest: str
    manifest_digest: str
    signature: str
    signer_key: str = "skills-runtime"


@router.post("")
async def register_skill(request: RegisterSkillRequest, who: Actor = Depends(actor)):
    require_writer(who, "SKILLS_REGISTRY_WRITERS")
    manifest = dict(request.manifest)
    manifest["name"] = request.name
    manifest["version"] = request.version
    if manifest.get("self_promotion") is not False or manifest.get("external_writes") is not False:
        raise HTTPException(400, "unsafe_skill_manifest")
    record = SkillRecord(identity=SkillIdentity(name=request.name, version=request.version, digest=manifest_digest(manifest)), stage=SkillStage.DRAFT, manifest=manifest)
    try:
        await registry.register(record)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    await evidence.append(skill_name=request.name, version=request.version, event_type="skill_registered", payload={"actor": who.subject, "digest": record.identity.digest})
    return record


@router.get("/{name}/{version}")
async def get_skill(name: str, version: str, _: Actor = Depends(actor)):
    try:
        return await registry.get(name, version)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.put("/{name}/{version}/evidence")
async def update_evidence(name: str, version: str, request: EvidenceUpdate, who: Actor = Depends(actor)):
    require_writer(who, "SKILLS_EVIDENCE_WRITERS")
    record = await registry.get(name, version)
    if record.stage in {SkillStage.VALIDATED, SkillStage.PRODUCTION}:
        raise HTTPException(409, "evidence_locked_after_validation")
    updates = request.model_dump(exclude_none=True)
    artifacts = updates.pop("artifacts", [])
    if updates.get("tests_passed") is True and not (updates.get("ci_run_id") or record.evidence.ci_run_id):
        raise HTTPException(400, "tests_passed_requires_ci_run_id")
    for key, value in updates.items():
        setattr(record.evidence, key, value)
    for item in artifacts:
        if item not in record.evidence.artifacts:
            record.evidence.artifacts.append(item)
    await registry.register(record)
    await evidence.append(skill_name=name, version=version, event_type="machine_evidence_updated", payload={"actor": who.subject, "fields": sorted(updates), "artifacts": artifacts})
    return record


@router.post("/{name}/{version}/bundles")
async def register_bundle(name: str, version: str, request: BundleRequest, who: Actor = Depends(actor)):
    require_writer(who, "SKILLS_BUNDLE_WRITERS")
    try:
        await bundles.register_verified(name=name, version=version, attestation=BundleAttestation(**request.model_dump()))
        return {"registered": True, "bundle_digest": request.bundle_digest}
    except (PermissionError, KeyError) as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/{name}/{version}/promote")
async def promote(name: str, version: str, request: PromotionRequest, who: Actor = Depends(actor)):
    try:
        record = await registry.get(name, version)
        if request.target is SkillStage.PRODUCTION:
            if who.actor_type != "human":
                raise HTTPException(403, "production_promotion_requires_human_actor")
            record.evidence.critical_human_approval = await approvals.approved_for(skill_name=name, version=version, evidence=approval_snapshot(record))
        promoted = await runtime.promote(record, request.target)
        if promoted.stage is SkillStage.PRODUCTION:
            await controls.set_enabled(name=name, version=version, enabled=True, actor=who.subject, reason="production_promotion")
        return promoted
    except (PermissionError, KeyError) as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/{name}/{version}/approvals")
async def request_approval(name: str, version: str, who: Actor = Depends(actor)):
    record = await registry.get(name, version)
    if record.stage is not SkillStage.VALIDATED:
        raise HTTPException(409, "approval_only_from_validated")
    return await approvals.request(skill_name=name, version=version, requested_by=who.subject, evidence=approval_snapshot(record))


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(approval_id: int, request: ApprovalDecision, who: Actor = Depends(actor)):
    if who.actor_type != "human":
        raise HTTPException(403, "human_approver_required")
    try:
        return await approvals.decide(approval_id=approval_id, approved=request.approved, decided_by=who.subject, reason=request.reason)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.put("/{name}/{version}/control")
async def set_control(name: str, version: str, request: ControlRequest, who: Actor = Depends(actor)):
    if request.enabled and who.actor_type != "human":
        raise HTTPException(403, "kill_switch_reenable_requires_human")
    return await controls.set_enabled(name=name, version=version, enabled=request.enabled, actor=who.subject, reason=request.reason)


@router.post("/{name}/{version}/revoke")
async def revoke(name: str, version: str, request: RevokeRequest, who: Actor = Depends(actor)):
    if who.actor_type != "human":
        raise HTTPException(403, "revocation_requires_human_actor")
    return await controls.revoke(name=name, version=version, actor=who.subject, reason=request.reason)


@router.post("/{name}/{version}/rollback")
async def rollback(name: str, version: str, request: RollbackRequest, who: Actor = Depends(actor)):
    if who.actor_type != "human":
        raise HTTPException(403, "rollback_requires_human_actor")
    try:
        await controls.rollback(name=name, from_version=version, to_version=request.to_version, actor=who.subject, reason=request.reason)
        await evidence.append(skill_name=name, version=version, event_type="skill_rollback", payload={"from_version": version, "to_version": request.to_version, "actor": who.subject, "reason": request.reason})
        return {"rolled_back": True, "from_version": version, "to_version": request.to_version}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{name}/{version}/authorize-execution")
async def authorize_execution(name: str, version: str, _: Actor = Depends(actor)):
    try:
        execution_id = await authorizer.authorize(name=name, version=version)
        return {"execution_id": str(execution_id), "authorized": True}
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
