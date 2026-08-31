from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path

from app.skills_runtime.openbao import OpenBaoTransitSigner


@dataclass(frozen=True)
class SignedBundle:
    skill_name: str
    version: str
    bundle_digest: str
    manifest_digest: str
    signature: str
    signer_key: str


def _canonical_manifest(manifest: dict) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build_deterministic_bundle(skill_dir: Path) -> bytes:
    if not skill_dir.is_dir():
        raise ValueError("skill_dir_missing")
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", compresslevel=9, mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
                rel = path.relative_to(skill_dir).as_posix()
                info = tf.gettarinfo(str(path), arcname=rel)
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.pax_headers = {}
                with path.open("rb") as f:
                    tf.addfile(info, f)
    return compressed.getvalue()


async def sign_bundle(*, skill_dir: Path, signer: OpenBaoTransitSigner, key_name: str) -> SignedBundle:
    manifest = json.loads((skill_dir / "manifest.json").read_text())
    blob = build_deterministic_bundle(skill_dir)
    bundle_digest = hashlib.sha256(blob).hexdigest()
    manifest_digest = hashlib.sha256(_canonical_manifest(manifest)).hexdigest()
    signature = await signer.sign_digest(bundle_digest, key_name=key_name)
    return SignedBundle(
        skill_name=manifest["name"],
        version=manifest["version"],
        bundle_digest=bundle_digest,
        manifest_digest=manifest_digest,
        signature=signature,
        signer_key=key_name,
    )


async def verify_bundle(*, skill_dir: Path, signed: SignedBundle, signer: OpenBaoTransitSigner) -> bool:
    current = hashlib.sha256(build_deterministic_bundle(skill_dir)).hexdigest()
    if current != signed.bundle_digest:
        return False
    return await signer.verify_digest(current, signature=signed.signature, key_name=signed.signer_key)
