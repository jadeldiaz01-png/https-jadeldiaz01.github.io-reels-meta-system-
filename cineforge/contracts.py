from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class JobState(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    POLICY_CHECK = "POLICY_CHECK"
    READY = "READY"
    RENDERING = "RENDERING"
    QC = "QC"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    DELIVERED = "DELIVERED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class GateDecision(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


@dataclass(frozen=True)
class VisualBible:
    palette: list[str]
    contrast: str
    color_temperature: str
    key_light_direction: str
    atmosphere: str
    default_focal_length_mm: int
    depth_of_field: str
    motion_blur: str
    continuity_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ShotContract:
    shot_id: str
    scene_id: str
    subject: str
    action: str
    blocking: str
    shot_size: Literal["ECU", "CU", "MCU", "MS", "MLS", "WS", "EWS", "INSERT", "REACTION"]
    focal_length_mm: int
    camera_height: str
    camera_angle: str
    camera_movement: str
    movement_motivation: str
    focus_plan: str
    lighting_plan: str
    exposure_notes: str
    white_balance_notes: str
    physics_constraints: list[str]
    continuity_constraints: list[str]
    entry_frame: str
    exit_frame: str
    duration_seconds: float


@dataclass(frozen=True)
class GenerationAttempt:
    attempt_id: str
    shot_id: str
    provider: str
    model: str
    prompt_hash: str
    reference_asset_ids: list[str]
    estimated_cost_usd: float
    actual_cost_usd: float | None = None
    output_uri: str | None = None
    output_sha256: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QCResult:
    asset_id: str
    technical: GateDecision
    visual: GateDecision
    audio: GateDecision
    continuity: GateDecision
    policy: GateDecision
    reasons: list[str]

    @property
    def accepted(self) -> bool:
        return all(
            gate == GateDecision.PASS
            for gate in (self.technical, self.visual, self.audio, self.continuity, self.policy)
        )
