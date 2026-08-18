from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest

from app.skills_runtime.approval import approval_digest
from app.skills_runtime.bundle import build_deterministic_bundle
from app.skills_runtime.identity import WorkloadTokenProvider
from app.skills_runtime.openbao import OpenBaoTransitSigner


def test_bundle_is_byte_for_byte_deterministic(tmp_path: Path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "manifest.json").write_text('{"name":"x","version":"1"}')
    (skill / "SKILL.md").write_text("hello")
    first = build_deterministic_bundle(skill)
    second = build_deterministic_bundle(skill)
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def test_bundle_digest_changes_when_content_changes(tmp_path: Path):
    skill = tmp_path / "skill"
    skill.mkdir()
    path = skill / "manifest.json"
    path.write_text('{"name":"x","version":"1"}')
    before = hashlib.sha256(build_deterministic_bundle(skill)).hexdigest()
    path.write_text('{"name":"x","version":"2"}')
    after = hashlib.sha256(build_deterministic_bundle(skill)).hexdigest()
    assert before != after


def test_transit_digest_input_is_base64_of_sha256_bytes():
    digest = "00" * 32
    assert OpenBaoTransitSigner._digest_input(digest) == base64.b64encode(bytes(32)).decode()
    with pytest.raises(ValueError, match="digest_must_be_sha256_hex"):
        OpenBaoTransitSigner._digest_input("abc")


def test_workload_token_provider_fails_closed_when_sink_missing(tmp_path: Path):
    provider = WorkloadTokenProvider(str(tmp_path / "missing"))
    with pytest.raises(RuntimeError, match="openbao_workload_identity_unavailable"):
        provider.get()


def test_approval_digest_is_bound_to_evidence_snapshot():
    a = approval_digest("skill", "1", "PRODUCTION", {"revision": 1})
    b = approval_digest("skill", "1", "PRODUCTION", {"revision": 2})
    assert a != b
