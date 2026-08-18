from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.skills_runtime.approval import PostgresApprovalService
from app.skills_runtime.bundle_store import BundleAttestation, PostgresBundleStore
from app.skills_runtime.controls import PostgresRuntimeControls
from app.skills_runtime.database import create_engine_from_env
from app.skills_runtime.evidence import PostgresEvidenceLedger
from app.skills_runtime.execution import SkillExecutionAuthorizer
from app.skills_runtime.lifecycle import SkillLifecycle
from app.skills_runtime.models import SkillRecord, SkillStage
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


def approval_snapshot(record: SkillRecord) -> dict:
    snapshot = record.model_dump(mode="json")
    snapshot["evidence"]["critical_human_approval"] = False
    return snapshot


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


@router.get("/{name}/{version}")
async def get_skill(name: str, version: str, _: Actor = Depends(actor)):
    try:
        return await registry.get(name, version)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{name}/{version}/bundles")
async def register_bundle(name: str, version: str, request: BundleRequest, _: Actor = Depends(actor)):
    try:
        await bundles.register_verified(name=name, version=version, attestation=BundleAttestation(**request.model_dump()))
        return {"registered": True, "bundle_digest": request.bundle_digest}
    except (PermissionError, KeyError) as exc:
        raise HTTPException(403, str(exc)) from exc


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
