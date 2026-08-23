from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import GateDecision


@dataclass(frozen=True)
class ImageQualityProfile:
    name: str
    aspect_ratio: str
    fps: float
    color_space: str
    transfer: str
    dynamic_range_priority: bool
    highlight_rolloff_priority: bool
    shadow_detail_priority: bool
    natural_motion_priority: bool
    layered_depth_priority: bool
    specular_reflection_priority: bool
    subject_background_separation_priority: bool
    stable_horizon_priority: bool
    text_independent_storytelling_priority: bool


@dataclass(frozen=True)
class ImageQualityProbe:
    aspect_ratio: str
    fps: float
    color_space: str
    transfer: str
    clipped_highlights_ratio: float
    crushed_shadows_ratio: float
    flicker_score: float
    jitter_score: float
    blur_consistency_score: float
    horizon_stability_score: float
    subject_separation_score: float
    layered_depth_score: float
    specular_detail_score: float
    compression_artifact_score: float


@dataclass(frozen=True)
class RenderCapability:
    provider: str
    model: str
    supports_reference_consistency: bool
    supports_image_to_video: bool
    supports_high_dynamic_range_source: bool
    supports_motion_control: bool
    supports_camera_control: bool
    supports_2k_or_higher_source: bool
    supports_audio: bool
    historical_visual_qc_pass_rate: float
    estimated_cost_usd: float


REFERENCE_VIDEO_PROFILE = ImageQualityProfile(
    name="loaded_reference_natural_sunset_action",
    aspect_ratio="9:16",
    fps=30.0,
    color_space="bt709",
    transfer="bt709",
    dynamic_range_priority=True,
    highlight_rolloff_priority=True,
    shadow_detail_priority=True,
    natural_motion_priority=True,
    layered_depth_priority=True,
    specular_reflection_priority=True,
    subject_background_separation_priority=True,
    stable_horizon_priority=True,
    text_independent_storytelling_priority=True,
)


def reference_quality_gate(probe: ImageQualityProbe) -> tuple[GateDecision, list[str]]:
    reasons: list[str] = []
    if probe.aspect_ratio != "9:16":
        reasons.append("aspect_ratio_not_9_16")
    if abs(probe.fps - 30.0) > 0.5:
        reasons.append("cadence_not_30fps")
    if probe.color_space.lower() != "bt709" or probe.transfer.lower() != "bt709":
        reasons.append("delivery_color_not_bt709")
    if probe.clipped_highlights_ratio > 0.03:
        reasons.append("excessive_highlight_clipping")
    if probe.crushed_shadows_ratio > 0.08:
        reasons.append("excessive_shadow_crush")
    if probe.flicker_score > 0.10:
        reasons.append("flicker_above_floor")
    if probe.jitter_score > 0.12:
        reasons.append("camera_jitter_above_floor")
    if probe.blur_consistency_score < 0.75:
        reasons.append("unnatural_motion_blur")
    if probe.horizon_stability_score < 0.85:
        reasons.append("unstable_horizon")
    if probe.subject_separation_score < 0.70:
        reasons.append("weak_subject_background_separation")
    if probe.layered_depth_score < 0.65:
        reasons.append("insufficient_fore_mid_background_depth")
    if probe.specular_detail_score < 0.60:
        reasons.append("specular_reflection_detail_lost")
    if probe.compression_artifact_score > 0.12:
        reasons.append("compression_artifacts_above_floor")
    return (GateDecision.FAIL if reasons else GateDecision.PASS, reasons)


def choose_render_capability(
    capabilities: Iterable[RenderCapability],
    *,
    reference_required: bool,
    complex_motion: bool,
    camera_control_required: bool,
    premium_source_required: bool = True,
) -> RenderCapability:
    candidates = list(capabilities)
    if reference_required:
        candidates = [c for c in candidates if c.supports_reference_consistency and c.supports_image_to_video]
    if complex_motion:
        candidates = [c for c in candidates if c.supports_motion_control]
    if camera_control_required:
        candidates = [c for c in candidates if c.supports_camera_control]
    if premium_source_required:
        preferred = [c for c in candidates if c.supports_2k_or_higher_source]
        if preferred:
            candidates = preferred
    if not candidates:
        raise ValueError("no_render_capability_meets_quality_floor")

    # Quality-first routing. Cost only breaks near-quality ties; it never overrides the floor.
    return max(
        candidates,
        key=lambda c: (round(c.historical_visual_qc_pass_rate, 3), -c.estimated_cost_usd),
    )
