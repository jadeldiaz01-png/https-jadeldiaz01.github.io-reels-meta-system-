from __future__ import annotations

from collections.abc import Iterable

from app.skills_runtime.models import SkillRecord


class SkillRegistry:
    """In-process registry boundary; production storage adapters can persist the same records."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], SkillRecord] = {}

    def register(self, record: SkillRecord) -> SkillRecord:
        key = (record.identity.name, record.identity.version)
        existing = self._records.get(key)
        if existing and existing.identity.digest != record.identity.digest:
            raise ValueError("immutable_version_digest_conflict")
        self._records[key] = record
        return record

    def get(self, name: str, version: str) -> SkillRecord:
        try:
            return self._records[(name, version)]
        except KeyError as exc:
            raise KeyError("skill_not_registered") from exc

    def list(self) -> Iterable[SkillRecord]:
        return tuple(self._records.values())
