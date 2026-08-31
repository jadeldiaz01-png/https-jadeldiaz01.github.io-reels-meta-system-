from pathlib import Path

import pytest

from app.vault import VaultDocument, VaultGenerator


def test_vault_document_keeps_provenance(tmp_path: Path):
    generator = VaultGenerator(tmp_path)
    doc = VaultDocument(slug="lesson-01", title="Lesson 01", body="Verified body",
                        source_urls=("https://example.com/source",), copyright_status="verified",
                        factuality_status="verified")
    path = generator.write("02-modules", doc)
    text = path.read_text(encoding="utf-8")
    assert "content_sha256:" in text
    assert "https://example.com/source" in text
    assert "copyright_status: verified" in text
    assert "factuality_status: verified" in text


def test_vault_rejects_path_traversal_slug(tmp_path: Path):
    with pytest.raises(ValueError, match="invalid_slug"):
        VaultGenerator(tmp_path).write("02-modules", VaultDocument(slug="../escape", title="x", body="x"))
