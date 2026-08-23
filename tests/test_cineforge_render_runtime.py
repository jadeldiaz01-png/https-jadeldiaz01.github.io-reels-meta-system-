import pytest

from cineforge.render_runtime import (
    ProviderRuntimeCapability,
    RuntimeState,
    ShotRequirements,
    choose_runtime_provider,
)


def provider(name, *, available=True, refs=False, end=False, audio=True, hd=True, identity=.8, temporal=.8, fidelity=.8):
    return ProviderRuntimeCapability(
        provider="runtime", model=name, available=available,
        text_to_video=True, image_to_video=True, video_to_video=False,
        reference_images=refs, end_frame=end, native_audio=audio,
        max_duration_s=15, supports_9_16=True, supports_1080p=hd,
        identity_consistency=identity, temporal_coherence=temporal, prompt_fidelity=fidelity,
    )


def test_identity_and_motion_route_to_strongest_eligible_provider():
    generic = provider("generic", refs=True, identity=.75, temporal=.78, fidelity=.9)
    consistent = provider("consistent", refs=True, identity=.95, temporal=.9, fidelity=.85)
    result = choose_runtime_provider(
        [generic, consistent],
        ShotRequirements(needs_identity_consistency=True, needs_reference_images=True, complex_motion=True),
    )
    assert result.model == "consistent"


def test_unavailable_workspace_fails_closed():
    unavailable = provider("video-model", available=False, refs=True)
    with pytest.raises(RuntimeError, match=RuntimeState.PROVIDER_UNAVAILABLE.value):
        choose_runtime_provider([unavailable], ShotRequirements(needs_reference_images=True))
