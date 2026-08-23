from cineforge.contracts import GateDecision
from cineforge.image_quality import (
    ImageQualityProbe,
    RenderCapability,
    choose_render_capability,
    reference_quality_gate,
)


def test_reference_quality_profile_passes_good_probe():
    probe = ImageQualityProbe(
        aspect_ratio="9:16",
        fps=30.0,
        color_space="bt709",
        transfer="bt709",
        clipped_highlights_ratio=0.01,
        crushed_shadows_ratio=0.03,
        flicker_score=0.02,
        jitter_score=0.04,
        blur_consistency_score=0.90,
        horizon_stability_score=0.95,
        subject_separation_score=0.86,
        layered_depth_score=0.84,
        specular_detail_score=0.80,
        compression_artifact_score=0.03,
    )
    decision, reasons = reference_quality_gate(probe)
    assert decision == GateDecision.PASS
    assert reasons == []


def test_reference_quality_profile_rejects_flat_unstable_image():
    probe = ImageQualityProbe(
        aspect_ratio="9:16",
        fps=30.0,
        color_space="bt709",
        transfer="bt709",
        clipped_highlights_ratio=0.08,
        crushed_shadows_ratio=0.12,
        flicker_score=0.2,
        jitter_score=0.2,
        blur_consistency_score=0.5,
        horizon_stability_score=0.6,
        subject_separation_score=0.5,
        layered_depth_score=0.4,
        specular_detail_score=0.4,
        compression_artifact_score=0.2,
    )
    decision, reasons = reference_quality_gate(probe)
    assert decision == GateDecision.FAIL
    assert "excessive_highlight_clipping" in reasons
    assert "unstable_horizon" in reasons
    assert "insufficient_fore_mid_background_depth" in reasons


def test_router_prefers_highest_qc_capability_that_meets_floor():
    low = RenderCapability("p1", "cheap", True, True, True, True, True, True, False, 0.82, 0.10)
    high = RenderCapability("p2", "premium", True, True, True, True, True, True, True, 0.94, 0.80)
    selected = choose_render_capability(
        [low, high], reference_required=True, complex_motion=True, camera_control_required=True
    )
    assert selected.model == "premium"


def test_router_fails_closed_when_no_model_meets_floor():
    weak = RenderCapability("p1", "weak", False, False, False, False, False, False, False, 0.99, 0.01)
    try:
        choose_render_capability(
            [weak], reference_required=True, complex_motion=True, camera_control_required=True
        )
    except ValueError as exc:
        assert str(exc) == "no_render_capability_meets_quality_floor"
    else:
        raise AssertionError("routing must fail closed")
