CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS external_action_intents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key text NOT NULL UNIQUE,
  action_class text NOT NULL,
  target text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  state text NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  external_id text,
  attempt integer NOT NULL DEFAULT 0 CHECK (attempt >= 0),
  lease_owner text,
  lease_expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_intents_reconcile ON external_action_intents(state, updated_at)
  WHERE state IN ('UNKNOWN','DISPATCHED','RECONCILING');

CREATE TABLE IF NOT EXISTS evidence_ledger (
  id bigserial PRIMARY KEY,
  intent_id uuid REFERENCES external_action_intents(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  payload jsonb NOT NULL,
  previous_hash text,
  event_hash text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id uuid NOT NULL REFERENCES external_action_intents(id) ON DELETE CASCADE,
  approval_class text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
  actor text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS webhook_receipts (
  provider text NOT NULL,
  event_id text NOT NULL,
  payload_sha256 text NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(provider,event_id)
);

CREATE TABLE IF NOT EXISTS kill_switches (
  scope text NOT NULL,
  scope_key text NOT NULL,
  enabled boolean NOT NULL DEFAULT false,
  reason text,
  changed_by text NOT NULL DEFAULT 'system',
  changed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(scope,scope_key)
);
