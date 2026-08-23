from dataclasses import replace

import pytest

from cineforge.free_providers import CATALOG, choose_free_provider


def test_free_router_prefers_enabled_local_provider():
    providers = [replace(p, enabled=(p.model == "wan2.2")) for p in CATALOG]
    selected = choose_free_provider(providers)
    assert selected.model == "wan2.2"


def test_free_router_rejects_consumer_trial_as_production_provider():
    providers = [replace(p, enabled=(p.provider == "runway-app")) for p in CATALOG]
    with pytest.raises(ValueError, match="no_free_provider_meets_runtime_floor"):
        choose_free_provider(providers)


def test_free_router_fails_closed_until_local_runtime_is_provisioned():
    with pytest.raises(ValueError, match="no_free_provider_meets_runtime_floor"):
        choose_free_provider(CATALOG)
