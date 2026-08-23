import pytest

from cineforge.zerogpu_client import ZeroGPUConfig, validate_runtime_metadata


def valid_metadata():
    h = "a" * 64
    return {
        "provider": "huggingface_zerogpu_large",
        "model": "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
        "model_revision": "deadbeef",
        "model_identity_sha256": h,
        "prompt_sha256": h,
        "output_sha256": h,
        "gpu_name": "NVIDIA RTX PRO 6000 Blackwell",
        "gpu_vram_gb": 48.0,
        "render_elapsed_s": 42.0,
        "evidence_status": "RENDERED_QC_PENDING",
    }


def test_space_id_must_be_owner_name():
    with pytest.raises(ValueError, match="invalid_huggingface_space_id"):
        ZeroGPUConfig("not-a-space-id").validate()


def test_runtime_metadata_accepts_real_gpu_shape():
    validate_runtime_metadata(valid_metadata())


def test_runtime_metadata_rejects_insufficient_vram():
    m = valid_metadata()
    m["gpu_vram_gb"] = 16
    with pytest.raises(ValueError, match="zerogpu_vram_below_wan22_floor"):
        validate_runtime_metadata(m)


def test_runtime_metadata_rejects_missing_provenance():
    m = valid_metadata()
    del m["output_sha256"]
    with pytest.raises(ValueError, match="zerogpu_metadata_missing"):
        validate_runtime_metadata(m)


def test_runtime_metadata_is_qc_pending_not_provider_enabled():
    m = valid_metadata()
    m["evidence_status"] = "MASTER_READY"
    with pytest.raises(ValueError, match="unexpected_zerogpu_evidence_state"):
        validate_runtime_metadata(m)
