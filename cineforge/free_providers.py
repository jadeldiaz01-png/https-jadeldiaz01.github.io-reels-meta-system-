from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProviderCostClass(str, Enum):
    FREE_LOCAL = "FREE_LOCAL"
    FREE_TRIAL = "FREE_TRIAL"
    MANUAL_ONLY = "MANUAL_ONLY"
    PAID_API = "PAID_API"


@dataclass(frozen=True)
class FreeProvider:
    provider: str
    model: str
    cost_class: ProviderCostClass
    automated: bool
    watermark_free: bool
    commercial_use_possible: bool
    requires_local_gpu: bool
    license_gate: str | None
    supports_text_to_video: bool
    supports_image_to_video: bool
    supports_audio: bool
    quality_rank: float
    enabled: bool = False


CATALOG: tuple[FreeProvider, ...] = (
    FreeProvider("local", "wan2.2", ProviderCostClass.FREE_LOCAL, True, True, True, True, "apache-2.0", True, True, False, 0.90),
    FreeProvider("local", "ltx-video-classic", ProviderCostClass.FREE_LOCAL, True, True, True, True, "apache-2.0/openrail-checkpoint", True, True, False, 0.86),
    FreeProvider("local", "hunyuanvideo-1.5", ProviderCostClass.FREE_LOCAL, True, True, True, True, "tencent-territory-license", True, True, False, 0.88),
    FreeProvider("runway-app", "free-plan-variable", ProviderCostClass.FREE_TRIAL, False, False, False, False, "consumer-plan-only", True, True, False, 0.72),
    FreeProvider("luma-app", "free-draft", ProviderCostClass.FREE_TRIAL, False, False, False, False, "personal-use-tier", True, True, False, 0.72),
)


def choose_free_provider(
    providers: Iterable[FreeProvider], *,
    require_automation: bool = True,
    require_watermark_free: bool = True,
    require_commercial_use: bool = True,
    minimum_quality_rank: float = 0.80,
) -> FreeProvider:
    candidates = []
    for p in providers:
        if not p.enabled:
            continue
        if p.cost_class is not ProviderCostClass.FREE_LOCAL:
            continue
        if require_automation and not p.automated:
            continue
        if require_watermark_free and not p.watermark_free:
            continue
        if require_commercial_use and not p.commercial_use_possible:
            continue
        if p.quality_rank < minimum_quality_rank:
            continue
        candidates.append(p)
    if not candidates:
        raise ValueError("no_free_provider_meets_runtime_floor")
    return max(candidates, key=lambda p: p.quality_rank)
