from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import GateDecision, QCResult


CRITICAL_VISUAL_DEFECTS = {
    "black_frames",
    "frozen_frames",
    "morphing",
    "character_drift",
    "warping",
    "severe_flicker",
    "anatomy_failure",
    "physics_failure",
    "focus_failure",
    "exposure_jump",
}


@dataclass(frozen=True)
class TechnicalProbe:
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    audio_sample_rate_hz: int
    duration_seconds: float
    decodes_cleanly: bool


def technical_gate(probe: TechnicalProbe) -> tuple[GateDecision, list[str]]:
    reasons: list[str] = []
    if probe.width < 1080 or probe.height < 1920:
        reasons.append("master_below_1080x1920")
    if probe.video_codec.lower() != "h264":
        reasons.append("video_codec_not_h264")
    if probe.audio_codec.lower() != "aac":
        reasons.append("audio_codec_not_aac")
    if probe.audio_sample_rate_hz < 48000:
        reasons.append("audio_sample_rate_below_48khz")
    if probe.fps <= 0 or probe.duration_seconds <= 0:
        reasons.append("invalid_timing")
    if not probe.decodes_cleanly:
        reasons.append("decode_integrity_failure")
    return (GateDecision.FAIL if reasons else GateDecision.PASS, reasons)


def visual_gate(defects: Iterable[str]) -> tuple[GateDecision, list[str]]:
    defects = sorted(set(defects))
    critical = [d for d in defects if d in CRITICAL_VISUAL_DEFECTS]
    if critical:
        return GateDecision.FAIL, critical
    return GateDecision.PASS, defects


def aggregate_qc(
    asset_id: str,
    technical: tuple[GateDecision, list[str]],
    visual: tuple[GateDecision, list[str]],
    audio: GateDecision,
    continuity: GateDecision,
    policy: GateDecision,
) -> QCResult:
    reasons = list(technical[1]) + list(visual[1])
    if audio != GateDecision.PASS:
        reasons.append("audio_gate_failed")
    if continuity != GateDecision.PASS:
        reasons.append("continuity_gate_failed")
    if policy != GateDecision.PASS:
        reasons.append("policy_gate_failed")
    return QCResult(
        asset_id=asset_id,
        technical=technical[0],
        visual=visual[0],
        audio=audio,
        continuity=continuity,
        policy=policy,
        reasons=reasons,
    )
