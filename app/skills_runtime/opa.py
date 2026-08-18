from __future__ import annotations

import os

import httpx


class OpaSkillPolicyClient:
    def __init__(self, *, url: str | None = None) -> None:
        self.url = (url or os.getenv("OPA_URL", "")).rstrip("/")

    async def evaluate(self, payload: dict, *, decision: str = "promotion") -> dict:
        if not self.url:
            raise RuntimeError("opa_unavailable")
        if decision not in {"promotion", "execution"}:
            raise ValueError("unsupported_opa_decision")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.url}/v1/data/agia/skills/{decision}",
                    json={"input": payload},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("opa_unavailable") from exc
        result = response.json().get("result")
        if not isinstance(result, dict) or "allow" not in result:
            raise RuntimeError("opa_invalid_decision")
        return result
