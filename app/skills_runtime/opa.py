from __future__ import annotations

import os

import httpx


class OpaSkillPolicyClient:
    def __init__(self, *, url: str | None = None) -> None:
        self.url = (url or os.getenv("OPA_URL", "")).rstrip("/")

    async def evaluate(self, payload: dict) -> dict:
        if not self.url:
            raise RuntimeError("opa_unavailable")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self.url}/v1/data/agia/skills/promotion",
                json={"input": payload},
            )
            response.raise_for_status()
            result = response.json().get("result")
            if not isinstance(result, dict) or "allow" not in result:
                raise RuntimeError("opa_invalid_decision")
            return result
