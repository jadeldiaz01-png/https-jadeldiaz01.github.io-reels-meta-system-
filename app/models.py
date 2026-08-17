from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IntentState(StrEnum):
    INTENT_CREATED = "INTENT_CREATED"
    AUTHORIZED = "AUTHORIZED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    FAILED_FINAL = "FAILED_FINAL"


class ActionClass(StrEnum):
    RESEARCH = "research"
    CONTENT_DRAFT = "content_draft"
    COURSE_BUILD = "course_build"
    PUBLISH_REEL = "publish_reel"
    CREATE_OFFER = "create_offer"
    FULFILL_ORDER = "fulfill_order"
    CUSTOMER_MESSAGE = "customer_message"
    CHANGE_PRICE = "change_price"


class ExternalActionIntent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    idempotency_key: str
    action_class: ActionClass
    target: str
    payload: dict[str, Any] = Field(default_factory=dict)
    state: IntentState = IntentState.INTENT_CREATED
    approved: bool = False
    external_id: str | None = None
    attempt: int = 0
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    allowed: bool
    approval_required: bool = False
    reasons: list[str] = Field(default_factory=list)
