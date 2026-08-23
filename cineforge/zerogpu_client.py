from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ZeroGPUConfig:
    space_id: str
    hf_token: str | None = None

    def validate(self) -> None:
        if "/" not in self.space_id or self.space_id.startswith("/") or self.space_id.endswith("/"):
            raise ValueError("invalid_huggingface_space_id")


@dataclass(frozen=True)
class ZeroGPURenderResult:
    local_video_path: str
    metadata: dict[str, Any]


def validate_runtime_metadata(metadata: dict[str, Any]) -> None:
    required = {
        "provider",
        "model",
        "model_revision",
        "model_identity_sha256",
        "prompt_sha256",
        "output_sha256",
        "gpu_name",
        "gpu_vram_gb",
        "render_elapsed_s",
        "evidence_status",
    }
    missing = sorted(required - set(metadata))
    if missing:
        raise ValueError(f"zerogpu_metadata_missing:{','.join(missing)}")
    if metadata["provider"] != "huggingface_zerogpu_large":
        raise ValueError("unexpected_zerogpu_provider")
    if float(metadata["gpu_vram_gb"]) < 24:
        raise ValueError("zerogpu_vram_below_wan22_floor")
    if metadata["evidence_status"] != "RENDERED_QC_PENDING":
        raise ValueError("unexpected_zerogpu_evidence_state")
    for key in ("model_identity_sha256", "prompt_sha256", "output_sha256"):
        value = str(metadata[key])
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
            raise ValueError(f"invalid_sha256:{key}")


def render_via_zerogpu(
    config: ZeroGPUConfig,
    *,
    prompt: str,
    seed: int = 321,
    steps: int = 16,
) -> ZeroGPURenderResult:
    """Invoke the user's configured Space. Import is lazy so core CineForge has no Gradio dependency."""
    config.validate()
    if len(prompt.strip()) < 20:
        raise ValueError("prompt_too_short")
    if not 8 <= steps <= 24:
        raise ValueError("steps_outside_governed_smoke_range")

    from gradio_client import Client, handle_file

    client = Client(config.space_id, token=config.hf_token)
    result = client.predict(prompt, int(seed), int(steps), api_name="/smoke")
    if not isinstance(result, (list, tuple)) or len(result) != 2:
        raise RuntimeError("unexpected_zerogpu_response")

    video_ref, metadata_text = result
    if isinstance(video_ref, dict):
        local_path = video_ref.get("path") or video_ref.get("name")
    else:
        local_path = str(video_ref)
    if not local_path or not Path(local_path).exists():
        raise RuntimeError("zerogpu_video_not_materialized")

    metadata = json.loads(str(metadata_text))
    validate_runtime_metadata(metadata)
    return ZeroGPURenderResult(local_video_path=local_path, metadata=metadata)
