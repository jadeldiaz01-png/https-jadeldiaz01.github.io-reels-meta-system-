from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderReadiness(str, Enum):
    READY = "READY"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CREDITS_UNAVAILABLE = "CREDITS_UNAVAILABLE"
    AUTH_UNAVAILABLE = "AUTH_UNAVAILABLE"


@dataclass(frozen=True)
class ProviderWorkspaceSnapshot:
    provider: str
    authenticated: bool
    workspace: str | None
    available_video_models: tuple[str, ...]
    credits_available: bool | None = None


def readiness(snapshot: ProviderWorkspaceSnapshot) -> ProviderReadiness:
    if not snapshot.authenticated:
        return ProviderReadiness.AUTH_UNAVAILABLE
    if not snapshot.available_video_models:
        return ProviderReadiness.PROVIDER_UNAVAILABLE
    if snapshot.credits_available is False:
        return ProviderReadiness.CREDITS_UNAVAILABLE
    return ProviderReadiness.READY


def require_ready(snapshot: ProviderWorkspaceSnapshot) -> None:
    state = readiness(snapshot)
    if state is not ProviderReadiness.READY:
        raise RuntimeError(state.value)
