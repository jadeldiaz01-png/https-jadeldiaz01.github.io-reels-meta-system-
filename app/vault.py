from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VaultDocument:
    slug: str
    title: str
    body: str
    source_urls: tuple[str, ...] = ()
    copyright_status: str = "unverified"
    factuality_status: str = "unverified"


class VaultGenerator:
    """Writes portable Markdown; publication remains policy-gated elsewhere."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, section: str, doc: VaultDocument) -> Path:
        if not doc.slug.replace("-", "").isalnum():
            raise ValueError("invalid_slug")
        folder = self.root / section
        folder.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.sha256(doc.body.encode()).hexdigest()
        sources = "\n".join(f"  - {url}" for url in doc.source_urls) or "  []"
        markdown = (
            "---\n"
            f"title: {doc.title!r}\n"
            f"content_sha256: {content_hash}\n"
            f"copyright_status: {doc.copyright_status}\n"
            f"factuality_status: {doc.factuality_status}\n"
            "sources:\n"
            f"{sources}\n"
            "---\n\n"
            f"# {doc.title}\n\n{doc.body.rstrip()}\n"
        )
        path = folder / f"{doc.slug}.md"
        path.write_text(markdown, encoding="utf-8")
        return path
