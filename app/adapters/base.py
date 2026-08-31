from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import ExternalActionIntent


class PlatformAdapter(ABC):
    @abstractmethod
    async def validate_session(self) -> bool: ...

    @abstractmethod
    async def check_capabilities(self) -> set[str]: ...

    @abstractmethod
    async def prepare_action(self, intent: ExternalActionIntent) -> dict: ...

    @abstractmethod
    async def execute(self, intent: ExternalActionIntent) -> str: ...

    @abstractmethod
    async def get_status(self, external_id: str) -> str: ...

    @abstractmethod
    async def reconcile(self, intent: ExternalActionIntent) -> str | None: ...

    @abstractmethod
    async def cancel(self, external_id: str) -> bool: ...

    @abstractmethod
    async def healthcheck(self) -> bool: ...
