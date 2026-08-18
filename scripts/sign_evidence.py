from __future__ import annotations

import asyncio
import json
import os
import pathlib

from app.evidence_signing import OpenBaoTransitSigner, canonical_bytes


async def main() -> None:
    evidence_path = pathlib.Path(os.environ.get("EVIDENCE_PATH", "external-evidence.jsonl"))
    records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    bundle = {"schema_version": "1.0", "records": records}
    signer = OpenBaoTransitSigner(os.environ["BAO_ADDR"], os.environ["BAO_TOKEN"])
    signed = await signer.sign(bundle)
    output = {
        "bundle": bundle,
        "bundle_sha256": signed.sha256,
        "signature": signed.signature,
        "signing_key": signed.key_name,
    }
    pathlib.Path(os.environ.get("SIGNED_EVIDENCE_PATH", "signed-evidence-bundle.json")).write_text(
        json.dumps(output, sort_keys=True, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
