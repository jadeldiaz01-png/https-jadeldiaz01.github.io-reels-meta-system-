BEGIN;

CREATE TABLE IF NOT EXISTS skill_registry (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    digest TEXT NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('DRAFT','REVIEWED','TESTED','VALIDATED','PRODUCTION')),
    manifest JSONB NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    signature TEXT,
    signer_key TEXT,
    revision BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version),
    UNIQUE (name, version, digest)
);

CREATE TABLE IF NOT EXISTS skill_evidence_ledger (
    id BIGSERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    previous_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL UNIQUE,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skill_registry_stage ON skill_registry(stage);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_identity ON skill_evidence_ledger(skill_name, version, id);

REVOKE UPDATE, DELETE ON skill_evidence_ledger FROM PUBLIC;

COMMIT;
