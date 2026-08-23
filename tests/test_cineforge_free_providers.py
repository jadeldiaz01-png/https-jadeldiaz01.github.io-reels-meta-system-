from dataclasses import replace

import pytest

from cineforge.free_providers import CATALOG, LicenseRisk, choose_free_provider


def _enabled(*models: str):
    return [replace(p, enabled=(p.model in models)) for p in CATALOG]


def test_free_router_prefers_highest_quality_enabled_local_provider():
    providers = _enabled("wan2.2-ti2v-5b", "wan2.2-a14b")
    selected = choose_free_provider(providers)
    assert selected.model == "wan2.2-a14b"


def test_free_router_can_select_low_vram_framepack_when_capacity_is_small():
    providers = _enabled("framepack", "wan2.2-ti2v-5b")
    selected = choose_free_provider(providers, max_vram_gb=8.0)
    assert selected.model == "framepack"


def test_free_router_rejects_consumer_trial_as_production_provider():
    providers = _enabled("free-plan-variable")
    with pytest.raises(ValueError, match="no_free_provider_meets_runtime_floor"):
        choose_free_provider(providers)


def test_free_router_rejects_high_license_risk_by_default():
    providers = _enabled("hunyuanvideo-1.5")
    with pytest.raises(ValueError, match="no_free_provider_meets_runtime_floor"):
        choose_free_provider(providers)


def test_free_router_allows_high_license_risk_only_when_explicitly_permitted():
    providers = _enabled("hunyuanvideo-1.5")
    selected = choose_free_provider(providers, maximum_license_risk=LicenseRisk.HIGH)
    assert selected.model == "hunyuanvideo-1.5"


def test_audio_requirement_selects_only_audio_capable_free_local_model():
    providers = _enabled("ltx-2.x", "wan2.2-a14b")
    selected = choose_free_provider(
        providers,
        require_audio=True,
        maximum_license_risk=LicenseRisk.MEDIUM,
    )
    assert selected.model == "ltx-2.x"


def test_free_router_fails_closed_until_local_runtime_is_provisioned():
    with pytest.raises(ValueError, match="no_free_provider_meets_runtime_floor"):
        choose_free_provider(CATALOG)
