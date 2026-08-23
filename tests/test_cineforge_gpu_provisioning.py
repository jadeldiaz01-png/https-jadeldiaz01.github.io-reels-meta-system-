import pytest

from cineforge.gpu_provisioning import BackendType, GPUBackend, choose_backend, model_for_vram
from cineforge.smoke_render import SmokeRenderEvidence, digest_text


def _backend(name, vram, *, persistent=False, quota=None, available=True):
    return GPUBackend(
        name=name,
        backend_type=BackendType.PERSISTENT if persistent else BackendType.SHARED_API,
        min_vram_gb=vram,
        max_vram_gb=vram,
        free_quota_minutes_day=quota,
        free_quota_hours_week=None,
        automated=True,
        ephemeral=not persistent,
        queue_risk=0.0 if persistent else 0.45,
        quota_risk=0.0 if persistent else 0.85,
        persistence_score=1.0 if persistent else 0.35,
        automation_score=1.0 if persistent else 0.85,
        observed_available=available,
    )


def test_model_routing_by_vram():
    assert model_for_vram(8) == "framepack"
    assert model_for_vram(16) == "cogvideox-2b"
    assert model_for_vram(24) == "wan2.2-ti2v-5b"


def test_persistent_24gb_beats_shared_48gb_for_same_job():
    persistent = _backend("vps", 24, persistent=True)
    zero = _backend("zerogpu", 48, quota=5)
    selected = choose_backend([persistent, zero], required_vram_gb=24, estimated_gpu_minutes=3)
    assert selected.backend.name == "vps"


def test_zerogpu_rejected_if_job_exceeds_free_daily_quota():
    zero = _backend("zerogpu", 48, quota=5)
    with pytest.raises(ValueError, match="no_gpu_backend_meets_runtime_and_quota_floor"):
        choose_backend([zero], required_vram_gb=24, estimated_gpu_minutes=6)


def test_smoke_evidence_must_pass_every_gate():
    h = "a" * 64
    ev = SmokeRenderEvidence(
        provider="local",
        model="framepack",
        checkpoint_id="pinned-revision",
        checkpoint_sha256=h,
        prompt_sha256=digest_text("original cinematic smoke prompt"),
        output_sha256=h,
        duration_s=4.0,
        width=768,
        height=1360,
        fps=24.0,
        codec="h264",
        decode_integrity=True,
        visual_qc_passed=True,
        watermark_detected=False,
        policy_passed=True,
    )
    assert ev.eligible_to_enable is True


def test_smoke_evidence_blocks_watermark():
    h = "b" * 64
    ev = SmokeRenderEvidence(
        provider="shared",
        model="test",
        checkpoint_id="pinned",
        checkpoint_sha256=h,
        prompt_sha256=h,
        output_sha256=h,
        duration_s=4.0,
        width=720,
        height=1280,
        fps=24,
        codec="h264",
        decode_integrity=True,
        visual_qc_passed=True,
        watermark_detected=True,
        policy_passed=True,
    )
    assert ev.eligible_to_enable is False
