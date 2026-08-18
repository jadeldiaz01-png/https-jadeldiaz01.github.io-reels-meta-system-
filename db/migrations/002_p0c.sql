CREATE TABLE IF NOT EXISTS sandbox_effects (
  idempotency_key text PRIMARY KEY,
  external_id text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'CONFIRMED',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qualification_evidence (
  gate text PRIMARY KEY,
  status text NOT NULL CHECK (status IN ('PASS','FAIL','UNKNOWN','NOT_RUN')),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_sha256 text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intents_lease_reconcile
ON external_action_intents(state, lease_expires_at, updated_at)
WHERE state IN ('UNKNOWN','DISPATCHED','RECONCILING');
