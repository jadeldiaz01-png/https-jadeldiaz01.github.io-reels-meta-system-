from __future__ import annotations

import os

import httpx


class OpenBaoTransitSigner:
    """Signs/verifies digests through OpenBao Transit using workload-provided auth."""

    def __init__(self, *, address: str | None = None, token: str | None = None, key_name: str = "skills-runtime") -> None:
        self.address = (address or os.getenv("OPENBAO_ADDR", "")).rstrip("/")
        self.token = token or os.getenv("OPENBAO_TOKEN", "")
        self.key_name = key_name

    def _headers(self) -> dict[str, str]:
        if not self.address or not self.token:
            raise RuntimeError("openbao_workload_identity_unavailable")
        return {"X-Vault-Token": self.token}

    async def sign_digest(self, digest_b64: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.address}/v1/transit/sign/{self.key_name}",
                headers=self._headers(),
                json={"input": digest_b64, "prehashed": True, "hash_algorithm": "sha2-256"},
            )
            response.raise_for_status()
            return str(response.json()["data"]["signature"])

    async def verify_digest(self, digest_b64: str, signature: str) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.address}/v1/transit/verify/{self.key_name}",
                headers=self._headers(),
                json={"input": digest_b64, "signature": signature, "prehashed": True, "hash_algorithm": "sha2-256"},
            )
            response.raise_for_status()
            return bool(response.json()["data"]["valid"])
