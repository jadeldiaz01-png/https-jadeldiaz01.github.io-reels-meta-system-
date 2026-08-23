from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class RuntimeState(str, Enum):
    PLANNED = "PLANNED"
    PROVIDER_READY = "PROVIDER_READY"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RENDERING = "RENDERING"
    QC_PENDING = "QC_PENDING"
    MASTER_READY = "MASTER_READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ProviderRuntimeCapability:
    provider: str
    model: str
    available: bool
    text_to_video: bool
    image_to_video: bool
    video_to_video: bool
    reference_images: bool
    end_frame: bool
    native_audio: bool
    max_duration_s: int
    supports_9_16: bool
    supports_1080p: bool
    identity_consistency: float
    temporal_coherence: float
    prompt_fidelity: float


@dataclass(frozen=True)
class ShotRequirements:
    needs_identity_consistency: bool = False
    needs_reference_images: bool = False
    needs_end_frame: bool = False
    needs_native_audio: bool = False
    needs_1080p: bool = True
    complex_motion: bool = False


def choose_runtime_provider(
    providers: Iterable[ProviderRuntimeCapability], requirements: ShotRequirements
) -> ProviderRuntimeCapability:
    candidates = [p for p in providers if p.available and p.text_to_video and p.supports_9_16]
    if requirements.needs_reference_images:
        candidates = [p for p in candidates if p.reference_images]
    if requirements.needs_end_frame:
        candidates = [p for p in candidates if p.end_frame]
    if requirements.needs_native_audio:
        candidates = [p for p in candidates if p.native_audio]
    if requirements.needs_1080p:
        candidates = [p for p in candidates if p.supports_1080p]
    if not candidates:
        raise RuntimeError(RuntimeState.PROVIDER_UNAVAILABLE.value)

    def score(p: ProviderRuntimeCapability) -> tuple[float, float, float]:
        identity = p.identity_consistency if requirements.needs_identity_consistency else 0.0
        temporal = p.temporal_coherence if requirements.complex_motion else 0.0
        return (identity + temporal, p.prompt_fidelity, p.temporal_coherence)

    return max(candidates, key=score)
