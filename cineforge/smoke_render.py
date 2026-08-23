from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path


@dataclass(frozen=True)
class SmokeRenderEvidence:
    provider: str
    model: str
    checkpoint_id: str
    checkpoint_sha256: str
    prompt_sha256: str
    output_sha256: str
    duration_s: float
    width: int
    height: int
    fps: float
    codec: str
    decode_integrity: bool
    visual_qc_passed: bool
    watermark_detected: bool
    policy_passed: bool

    @property
    def eligible_to_enable(self) -> bool:
        return (
            3.0 <= self.duration_s <= 5.5
            and self.width > 0
            and self.height > 0
            and self.fps > 0
            and self.decode_integrity
            and self.visual_qc_passed
            and not self.watermark_detected
            and self.policy_passed
            and len(self.checkpoint_sha256) == 64
            and len(self.prompt_sha256) == 64
            and len(self.output_sha256) == 64
        )


def digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def digest_file(path: str | Path) -> str:
    p = Path(path)
    h = sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_evidence(evidence: SmokeRenderEvidence, path: str | Path) -> None:
    payload = asdict(evidence)
    payload["eligible_to_enable"] = evidence.eligible_to_enable
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
