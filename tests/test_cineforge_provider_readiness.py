from cineforge.provider_readiness import ProviderReadiness, ProviderWorkspaceSnapshot, readiness


def test_authenticated_workspace_without_video_models_is_unavailable():
    snap = ProviderWorkspaceSnapshot(
        provider="runway",
        authenticated=True,
        workspace="Jadel",
        available_video_models=(),
        credits_available=None,
    )
    assert readiness(snap) == ProviderReadiness.PROVIDER_UNAVAILABLE


def test_workspace_with_model_and_credits_is_ready():
    snap = ProviderWorkspaceSnapshot(
        provider="runway",
        authenticated=True,
        workspace="Jadel",
        available_video_models=("gen4.5",),
        credits_available=True,
    )
    assert readiness(snap) == ProviderReadiness.READY


def test_no_credits_blocks_even_when_model_exists():
    snap = ProviderWorkspaceSnapshot(
        provider="runway",
        authenticated=True,
        workspace="Jadel",
        available_video_models=("gen4.5",),
        credits_available=False,
    )
    assert readiness(snap) == ProviderReadiness.CREDITS_UNAVAILABLE
