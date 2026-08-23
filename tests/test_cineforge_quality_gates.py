from cineforge.contracts import GateDecision
from cineforge.quality_gates import TechnicalProbe, technical_gate, visual_gate


def test_valid_master_passes_technical_gate():
    probe = TechnicalProbe(
        width=1080,
        height=1920,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        audio_sample_rate_hz=48000,
        duration_seconds=20.0,
        decodes_cleanly=True,
    )
    decision, reasons = technical_gate(probe)
    assert decision == GateDecision.PASS
    assert reasons == []


def test_low_resolution_fails_technical_gate():
    probe = TechnicalProbe(
        width=720,
        height=1280,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        audio_sample_rate_hz=48000,
        duration_seconds=20.0,
        decodes_cleanly=True,
    )
    decision, reasons = technical_gate(probe)
    assert decision == GateDecision.FAIL
    assert "master_below_1080x1920" in reasons


def test_critical_visual_defect_fails_closed():
    decision, reasons = visual_gate(["morphing"])
    assert decision == GateDecision.FAIL
    assert reasons == ["morphing"]
