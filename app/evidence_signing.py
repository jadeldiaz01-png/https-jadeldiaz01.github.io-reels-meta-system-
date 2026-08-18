from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class SignedEvidence:
    sha256: str
    signature: str
    key_name: str


def canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class OpenBaoTransitSigner:
    """Signs qualification evidence with an OpenBao Transit signing key; no private key leaves OpenBao."""

    def __init__(self, address: str, token: str, key_name: str = "live-pilot-evidence", timeout: float = 10.0) -> None:
        if not address.startswith("https://"):
            raise ValueError("production_openbao_https_required")
        if not token or not key_name:
            raise ValueError("openbao_identity_and_key_required")
        self.address = address.rstrip("/")
        self.token = token
        self.key_name = key_name
        self.timeout = timeout

    async def sign(self, payload: dict) -> SignedEvidence:
        raw = canonical_bytes(payload)
        digest = hashlib.sha256(raw).hexdigest()
        encoded = base64.b64encode(raw).decode()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.address}/v1/transit/sign/{self.key_name}",
                headers={"X-Vault-Token": self.token},
                json={"input": encoded, "hash_algorithm": "sha2-256"},
            )
            response.raise_for_status()
            signature = response.json().get("data", {}).get("signature")
            if not isinstance(signature, str) or not signature:
                raise RuntimeError("openbao_signature_missing")
        return SignedEvidence(digest, signature, self.key_name)
