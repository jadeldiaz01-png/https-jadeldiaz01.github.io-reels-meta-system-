from __future__ import annotations

import base64
import os

import httpx

from app.skills_runtime.identity import WorkloadTokenProvider


class OpenBaoTransitSigner:
    """Signs/verifies SHA-256 digests through OpenBao Transit using workload identity."""

    def __init__(
        self,
        *,
        address: str | None = None,
        token_provider: WorkloadTokenProvider | None = None,
        key_name: str = "skills-runtime",
    ) -> None:
        self.address = (address or os.getenv("OPENBAO_ADDR", "")).rstrip("/")
        self.token_provider = token_provider or WorkloadTokenProvider()
        self.key_name = key_name

    def _headers(self) -> dict[str, str]:
        if not self.address:
            raise RuntimeError("openbao_address_unavailable")
        return {"X-Vault-Token": self.token_provider.get()}

    @staticmethod
    def _digest_input(digest_hex: str) -> str:
        try:
            raw = bytes.fromhex(digest_hex)
        except ValueError as exc:
            raise ValueError("digest_must_be_sha256_hex") from exc
        if len(raw) != 32:
            raise ValueError("digest_must_be_sha256_hex")
        return base64.b64encode(raw).decode()

    async def sign_digest(self, digest_hex: str, *, key_name: str | None = None) -> str:
        key = key_name or self.key_name
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.address}/v1/transit/sign/{key}/sha2-256",
                headers=self._headers(),
                json={"input": self._digest_input(digest_hex), "prehashed": True},
            )
            response.raise_for_status()
            return str(response.json()["data"]["signature"])

    async def verify_digest(self, digest_hex: str, signature: str, *, key_name: str | None = None) -> bool:
        key = key_name or self.key_name
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.address}/v1/transit/verify/{key}/sha2-256",
                headers=self._headers(),
                json={"input": self._digest_input(digest_hex), "signature": signature, "prehashed": True},
            )
            response.raise_for_status()
            return bool(response.json()["data"]["valid"])
