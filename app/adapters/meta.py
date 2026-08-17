from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from app.adapters.base import PlatformAdapter
from app.models import ExternalActionIntent


@dataclass(frozen=True)
class MetaConfig:
    access_token: str
    instagram_user_id: str
    graph_version: str
    base_url: str = "https://graph.facebook.com"


class MetaReelsAdapter(PlatformAdapter):
    """Official Graph API adapter. Requires an eligible professional account and explicit credentials."""

    def __init__(self, config: MetaConfig, *, timeout: float = 10.0) -> None:
        if not config.access_token or not config.instagram_user_id or not config.graph_version:
            raise ValueError("meta_credentials_and_graph_version_required")
        self.config = config
        self.timeout = timeout
        self._container_by_key: dict[str, str] = {}
        self._published_by_key: dict[str, str] = {}

    @property
    def api(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/{self.config.graph_version}"

    async def validate_session(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(
                    f"{self.api}/{self.config.instagram_user_id}",
                    params={"fields": "id,username", "access_token": self.config.access_token},
                )
                return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def check_capabilities(self) -> set[str]:
        return {"publish_reel", "reconcile"} if await self.validate_session() else set()

    async def prepare_action(self, intent: ExternalActionIntent) -> dict:
        video_url = intent.payload.get("video_url")
        if not isinstance(video_url, str) or not video_url.startswith("https://"):
            raise ValueError("public_https_video_url_required")
        return {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": str(intent.payload.get("caption", "")),
            "access_token": self.config.access_token,
        }

    async def execute(self, intent: ExternalActionIntent) -> str:
        if intent.idempotency_key in self._published_by_key:
            return self._published_by_key[intent.idempotency_key]
        payload = await self.prepare_action(intent)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            container_id = self._container_by_key.get(intent.idempotency_key)
            if not container_id:
                r = await client.post(f"{self.api}/{self.config.instagram_user_id}/media", data=payload)
                r.raise_for_status()
                container_id = str(r.json()["id"])
                self._container_by_key[intent.idempotency_key] = container_id

            for _ in range(20):
                status = await client.get(
                    f"{self.api}/{container_id}",
                    params={"fields": "status_code", "access_token": self.config.access_token},
                )
                status.raise_for_status()
                code = status.json().get("status_code")
                if code == "FINISHED":
                    break
                if code in {"ERROR", "EXPIRED"}:
                    raise RuntimeError(f"meta_container_{str(code).lower()}")
                await asyncio.sleep(3)
            else:
                raise TimeoutError("meta_container_not_finished")

            publish = await client.post(
                f"{self.api}/{self.config.instagram_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": self.config.access_token},
            )
            publish.raise_for_status()
            media_id = str(publish.json()["id"])
            self._published_by_key[intent.idempotency_key] = media_id
            return media_id

    async def get_status(self, external_id: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.api}/{external_id}",
                params={"fields": "id", "access_token": self.config.access_token},
            )
            return "CONFIRMED" if r.status_code == 200 else "UNKNOWN"

    async def reconcile(self, intent: ExternalActionIntent) -> str | None:
        # Durable production reconciliation must persist these mappings in PostgreSQL.
        return self._published_by_key.get(intent.idempotency_key)

    async def cancel(self, external_id: str) -> bool:
        return False

    async def healthcheck(self) -> bool:
        return await self.validate_session()
