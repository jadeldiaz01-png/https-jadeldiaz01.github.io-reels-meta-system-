from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProviderCostClass(str, Enum):
    FREE_LOCAL = "FREE_LOCAL"
    FREE_TRIAL = "FREE_TRIAL"
    MANUAL_ONLY = "MANUAL_ONLY"
    PAID_API = "PAID_API"


class LicenseRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


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
    license_risk: LicenseRisk
    supports_text_to_video: bool
    supports_image_to_video: bool
    supports_audio: bool
    supports_long_video: bool
    min_vram_gb: float | None
    benchmark_score: float | None
    quality_rank: float
    notes: str = ""
    enabled: bool = False


CATALOG: tuple[FreeProvider, ...] = (
    FreeProvider(
        "local", "wan2.2-ti2v-5b", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0", LicenseRisk.LOW, True, True, False, False, 24.0, None, 0.95,
        "Preferred first smoke-test target; 720p/24fps TI2V path and Diffusers/ComfyUI integration.",
    ),
    FreeProvider(
        "local", "wan2.2-a14b", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0", LicenseRisk.LOW, True, True, False, False, 24.0, None, 0.97,
        "Higher-quality path; official reference implementation recommends much larger VRAM for native inference.",
    ),
    FreeProvider(
        "local", "skyreels-v2", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "skywork-community-license", LicenseRisk.MEDIUM, True, True, False, True, None, 83.9, 0.96,
        "Strong open-model VBench result; supports diffusion-forcing/long-form workflows. License review required.",
    ),
    FreeProvider(
        "local", "framepack", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0-code-plus-model-license-check", LicenseRisk.MEDIUM, True, True, False, True, 6.0, None, 0.90,
        "Best low-VRAM candidate; long-video generation possible on consumer RTX GPUs. Check underlying model weights/license.",
    ),
    FreeProvider(
        "local", "open-sora-2.0", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0", LicenseRisk.LOW, True, False, False, False, None, 81.5, 0.88,
        "Open Apache-2.0 research pipeline; useful deterministic fallback and benchmark reference.",
    ),
    FreeProvider(
        "local", "cogvideox-2b", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0", LicenseRisk.LOW, True, False, False, False, 12.0, None, 0.82,
        "Lower-resource compatibility path; official project notes older GPUs can run 2B.",
    ),
    FreeProvider(
        "local", "cogvideox1.5-5b", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "cogvideox-commercial-registration", LicenseRisk.MEDIUM, True, True, False, False, 24.0, 80.3, 0.89,
        "Commercial use requires the model license/registration gate; do not auto-enable.",
    ),
    FreeProvider(
        "local", "mochi-1-preview", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "apache-2.0", LicenseRisk.LOW, True, False, False, False, 60.0, None, 0.84,
        "Good motion research baseline but expensive VRAM in official implementation; ComfyUI can reduce memory.",
    ),
    FreeProvider(
        "local", "ltx-video-classic", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "checkpoint-license-review", LicenseRisk.MEDIUM, True, True, False, False, None, None, 0.86,
        "Classic LTX path retained only after checkpoint-specific license verification.",
    ),
    FreeProvider(
        "local", "ltx-2.x", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "ltx-community-license", LicenseRisk.MEDIUM, True, True, True, False, None, None, 0.93,
        "Audio+video capable; entities above the license revenue threshold require paid commercial terms.",
    ),
    FreeProvider(
        "local", "hunyuanvideo-1.5", ProviderCostClass.FREE_LOCAL, True, True, True, True,
        "tencent-territory-license", LicenseRisk.HIGH, True, True, False, False, None, None, 0.88,
        "Territory/license gate required before any provisioning.",
    ),
    FreeProvider(
        "runway-app", "free-plan-variable", ProviderCostClass.FREE_TRIAL, False, False, False, False,
        "consumer-plan-only", LicenseRisk.HIGH, True, True, False, False, None, None, 0.72,
        "Consumer credits are not a durable free API runtime and current connected workspace has no video models enabled.",
    ),
    FreeProvider(
        "luma-app", "free-draft", ProviderCostClass.FREE_TRIAL, False, False, False, False,
        "consumer-personal-tier", LicenseRisk.HIGH, True, True, False, False, None, None, 0.72,
        "Free UI tier is not a durable automated production API and may watermark outputs.",
    ),
)


def choose_free_provider(
    providers: Iterable[FreeProvider], *,
    require_automation: bool = True,
    require_watermark_free: bool = True,
    require_commercial_use: bool = True,
    require_i2v: bool = False,
    require_audio: bool = False,
    max_vram_gb: float | None = None,
    maximum_license_risk: LicenseRisk = LicenseRisk.MEDIUM,
    minimum_quality_rank: float = 0.80,
) -> FreeProvider:
    risk_order = {LicenseRisk.LOW: 0, LicenseRisk.MEDIUM: 1, LicenseRisk.HIGH: 2}
    candidates: list[FreeProvider] = []
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
        if require_i2v and not p.supports_image_to_video:
            continue
        if require_audio and not p.supports_audio:
            continue
        if max_vram_gb is not None and p.min_vram_gb is not None and p.min_vram_gb > max_vram_gb:
            continue
        if risk_order[p.license_risk] > risk_order[maximum_license_risk]:
            continue
        if p.quality_rank < minimum_quality_rank:
            continue
        candidates.append(p)
    if not candidates:
        raise ValueError("no_free_provider_meets_runtime_floor")
    return max(
        candidates,
        key=lambda p: (
            p.quality_rank,
            p.benchmark_score if p.benchmark_score is not None else -1.0,
            -(p.min_vram_gb if p.min_vram_gb is not None else 999.0),
        ),
    )
