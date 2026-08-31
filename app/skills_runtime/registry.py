from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.skills_runtime.models import SkillRecord, SkillStage

_STAGE_ORDER = {
    SkillStage.DRAFT.value: 0,
    SkillStage.REVIEWED.value: 1,
    SkillStage.TESTED.value: 2,
    SkillStage.VALIDATED.value: 3,
    SkillStage.PRODUCTION.value: 4,
}


class SkillRegistry:
    """Async in-process registry for tests/dev; production should use PostgresSkillRegistry."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], SkillRecord] = {}

    async def register(self, record: SkillRecord) -> SkillRecord:
        key = (record.identity.name, record.identity.version)
        existing = self._records.get(key)
        if existing and existing.identity.digest != record.identity.digest:
            raise ValueError("immutable_version_digest_conflict")
        if existing and _STAGE_ORDER[record.stage.value] < _STAGE_ORDER[existing.stage.value]:
            raise ValueError("stage_regression_forbidden")
        self._records[key] = record
        return record

    async def get(self, name: str, version: str) -> SkillRecord:
        try:
            return self._records[(name, version)]
        except KeyError as exc:
            raise KeyError("skill_not_registered") from exc

    def list(self) -> Iterable[SkillRecord]:
        return tuple(self._records.values())


class PostgresSkillRegistry:
    """Durable registry enforcing immutable name+version digests and monotonic stages."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def register(self, record: SkillRecord) -> SkillRecord:
        async with self.engine.begin() as conn:
            existing = (await conn.execute(
                text("SELECT digest, stage, revision FROM skill_registry WHERE name=:name AND version=:version FOR UPDATE"),
                {"name": record.identity.name, "version": record.identity.version},
            )).mappings().one_or_none()
            if existing:
                if existing["digest"] != record.identity.digest:
                    raise ValueError("immutable_version_digest_conflict")
                if _STAGE_ORDER[record.stage.value] < _STAGE_ORDER[existing["stage"]]:
                    raise ValueError("stage_regression_forbidden")
                if record.revision < existing["revision"]:
                    raise ValueError("revision_regression_forbidden")

            await conn.execute(
                text("""
                    INSERT INTO skill_registry
                    (name, version, digest, stage, manifest, evidence, signature, signer_key, revision)
                    VALUES (:name, :version, :digest, :stage, CAST(:manifest AS jsonb), CAST(:evidence AS jsonb), :signature, :signer_key, :revision)
                    ON CONFLICT (name, version) DO UPDATE SET
                      stage=EXCLUDED.stage,
                      evidence=EXCLUDED.evidence,
                      signature=EXCLUDED.signature,
                      signer_key=EXCLUDED.signer_key,
                      revision=EXCLUDED.revision,
                      updated_at=now()
                    WHERE skill_registry.digest=EXCLUDED.digest
                """),
                {
                    "name": record.identity.name,
                    "version": record.identity.version,
                    "digest": record.identity.digest,
                    "stage": record.stage.value,
                    "manifest": json.dumps(record.manifest, sort_keys=True),
                    "evidence": record.evidence.model_dump_json(),
                    "signature": record.signature,
                    "signer_key": record.signer_key,
                    "revision": record.revision,
                },
            )
        return record

    async def get(self, name: str, version: str) -> SkillRecord:
        async with self.engine.connect() as conn:
            row = (await conn.execute(
                text("""
                    SELECT name, version, digest, stage, manifest, evidence, signature, signer_key, revision
                    FROM skill_registry WHERE name=:name AND version=:version
                """),
                {"name": name, "version": version},
            )).mappings().one_or_none()
        if row is None:
            raise KeyError("skill_not_registered")
        return SkillRecord.model_validate({
            "identity": {"name": row["name"], "version": row["version"], "digest": row["digest"]},
            "stage": row["stage"],
            "manifest": row["manifest"],
            "evidence": row["evidence"],
            "signature": row["signature"],
            "signer_key": row["signer_key"],
            "revision": row["revision"],
        })
