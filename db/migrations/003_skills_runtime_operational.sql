BEGIN;

CREATE TABLE IF NOT EXISTS skill_approvals (
    id BIGSERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    requested_stage TEXT NOT NULL CHECK (requested_stage IN ('PRODUCTION')),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED','CANCELLED')),
    requested_by TEXT NOT NULL,
    decided_by TEXT,
    reason TEXT,
    request_digest TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    UNIQUE (skill_name, version, requested_stage, request_digest)
);

CREATE INDEX IF NOT EXISTS idx_skill_approvals_pending
ON skill_approvals(skill_name, version, status);

CREATE TABLE IF NOT EXISTS skill_runtime_controls (
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (skill_name, version)
);

CREATE TABLE IF NOT EXISTS skill_bundles (
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    bundle_digest TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    signature TEXT NOT NULL,
    signer_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (skill_name, version, bundle_digest)
);

CREATE TABLE IF NOT EXISTS skill_execution_leases (
    execution_id UUID PRIMARY KEY,
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    bundle_digest TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('AUTHORIZED','RUNNING','SUCCEEDED','FAILED','REVOKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
