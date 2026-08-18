from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.skills_runtime.evidence import PostgresEvidenceLedger
from app.skills_runtime.openbao import OpenBaoTransitSigner
from app.skills_runtime.registry import PostgresSkillRegistry


@dataclass(frozen=True)
class BundleAttestation:
    bundle_digest: str
    manifest_digest: str
    signature: str
    signer_key: str = "skills-runtime"


def manifest_digest(manifest: dict) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


class PostgresBundleStore:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        registry: PostgresSkillRegistry,
        signer: OpenBaoTransitSigner,
        evidence: PostgresEvidenceLedger,
    ) -> None:
        self.engine = engine
        self.registry = registry
        self.signer = signer
        self.evidence = evidence

    async def register_verified(self, *, name: str, version: str, attestation: BundleAttestation) -> None:
        record = await self.registry.get(name, version)
        expected_manifest_digest = manifest_digest(record.manifest)
        if attestation.manifest_digest != expected_manifest_digest:
            raise PermissionError("bundle_manifest_digest_mismatch")
        if not await self.signer.verify_digest(
            attestation.bundle_digest,
            attestation.signature,
            key_name=attestation.signer_key,
        ):
            raise PermissionError("bundle_signature_invalid")

        async with self.engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO skill_bundles(skill_name,version,bundle_digest,manifest_digest,signature,signer_key)
                VALUES (:name,:version,:bundle_digest,:manifest_digest,:signature,:signer_key)
                ON CONFLICT (skill_name,version,bundle_digest) DO UPDATE
                SET manifest_digest=EXCLUDED.manifest_digest,
                    signature=EXCLUDED.signature,
                    signer_key=EXCLUDED.signer_key
            """), {
                "name": name,
                "version": version,
                "bundle_digest": attestation.bundle_digest,
                "manifest_digest": attestation.manifest_digest,
                "signature": attestation.signature,
                "signer_key": attestation.signer_key,
            })

        record.signature = attestation.signature
        record.signer_key = attestation.signer_key
        record.evidence.signature_verified = True
        if attestation.bundle_digest not in record.evidence.artifacts:
            record.evidence.artifacts.append(attestation.bundle_digest)
        await self.registry.register(record)
        await self.evidence.append(
            skill_name=name,
            version=version,
            event_type="bundle_verified",
            payload={
                "bundle_digest": attestation.bundle_digest,
                "manifest_digest": attestation.manifest_digest,
                "signer_key": attestation.signer_key,
            },
        )
