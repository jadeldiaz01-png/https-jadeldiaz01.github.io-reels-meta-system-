from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class BackendType(str, Enum):
    PERSISTENT = "PERSISTENT"
    SHARED_API = "SHARED_API"
    SESSION = "SESSION"


@dataclass(frozen=True)
class GPUBackend:
    name: str
    backend_type: BackendType
    min_vram_gb: float
    max_vram_gb: float | None
    free_quota_minutes_day: float | None
    free_quota_hours_week: float | None
    automated: bool
    ephemeral: bool
    queue_risk: float
    quota_risk: float
    persistence_score: float
    automation_score: float
    observed_available: bool = False


@dataclass(frozen=True)
class ProvisioningDecision:
    backend: GPUBackend
    model: str
    score: float
    reason: str


def model_for_vram(vram_gb: float) -> str:
    if vram_gb >= 24:
        return "wan2.2-ti2v-5b"
    if vram_gb >= 12:
        return "cogvideox-2b"
    if vram_gb >= 6:
        return "framepack"
    raise ValueError("gpu_vram_below_supported_floor")


def score_backend(b: GPUBackend, *, required_vram_gb: float, estimated_gpu_minutes: float) -> float:
    if not b.observed_available:
        return float("-inf")
    if b.max_vram_gb is not None and b.max_vram_gb < required_vram_gb:
        return float("-inf")
    if b.min_vram_gb > required_vram_gb and b.max_vram_gb is None:
        return float("-inf")
    if b.free_quota_minutes_day is not None and estimated_gpu_minutes > b.free_quota_minutes_day:
        return float("-inf")
    base = 0.0
    base += 35.0 * b.persistence_score
    base += 30.0 * b.automation_score
    base += 20.0 * (1.0 - b.queue_risk)
    base += 15.0 * (1.0 - b.quota_risk)
    if b.ephemeral:
        base -= 10.0
    return round(base, 3)


def choose_backend(
    backends: Iterable[GPUBackend], *,
    required_vram_gb: float,
    estimated_gpu_minutes: float,
) -> ProvisioningDecision:
    ranked: list[tuple[float, GPUBackend]] = []
    for backend in backends:
        score = score_backend(
            backend,
            required_vram_gb=required_vram_gb,
            estimated_gpu_minutes=estimated_gpu_minutes,
        )
        if score != float("-inf"):
            ranked.append((score, backend))
    if not ranked:
        raise ValueError("no_gpu_backend_meets_runtime_and_quota_floor")
    score, backend = max(ranked, key=lambda x: x[0])
    effective_vram = backend.max_vram_gb or backend.min_vram_gb
    return ProvisioningDecision(
        backend=backend,
        model=model_for_vram(effective_vram),
        score=score,
        reason="selected by persistence, automation, queue/quota risk and VRAM; quality floor is evaluated separately",
    )
