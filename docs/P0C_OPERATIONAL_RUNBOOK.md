# P0-C LIVE_PILOT Qualification Runbook

## Current decision

`LIVE_PILOT_NO_GO`

Do not enable external execution while qualification is running. The repository manifest is authoritative and fails closed on missing or non-PASS evidence.

## 1. GitHub protected environment

Create a GitHub Environment named exactly:

`live-pilot-qualification`

Require a human reviewer before jobs using this environment can access its protected secrets.

Configure only TEST/non-production provider credentials.

### Environment secrets

- `META_TEST_ACCESS_TOKEN`: access token for the dedicated Meta test/professional account only.
- `META_TEST_IG_USER_ID`: dedicated Instagram test/professional account ID.
- `STRIPE_TEST_SECRET_KEY`: must begin with `sk_test_`; live keys are rejected by the qualification harness.
- `BAO_QUALIFICATION_TOKEN`: short-lived OpenBao token restricted to Transit signing for the qualification evidence key.

### Environment variables

- `META_GRAPH_VERSION`: explicitly selected supported Graph API version.
- `META_TEST_VIDEO_URL`: public HTTPS URL for a non-sensitive qualification video asset.
- `STRIPE_TEST_EVIDENCE_ENDPOINT`: HTTPS endpoint returning the TEST evidence booleans expected by `scripts/qualify_external_test.py`.
- `BAO_ADDR`: HTTPS URL of the OpenBao qualification instance.
- `PITR_PGHOST`: isolated PostgreSQL qualification host.
- `PITR_PGPORT`: PostgreSQL port.
- `PITR_PGUSER`: least-privilege backup/recovery user appropriate for the drill.
- `PITR_PGDATA_SOURCE`: source data directory for the isolated drill.
- `PITR_BASEBACKUP_DIR`: disposable base-backup destination.
- `PITR_RESTORE_DIR`: disposable restore destination; never point to production data.
- `WAL_ARCHIVE_DIR`: WAL archive used by the isolated recovery drill.

Never store any of those secret values in Git, issues, PR comments, workflow logs, chat, or repository `.env` files.

## 2. Qualification runner

Register a dedicated self-hosted GitHub Actions runner with cumulative labels:

- `self-hosted`
- `linux`
- `x64`
- `live-pilot-qualifier`

The host must be isolated from production and must not contain live Meta, Stripe, payment, browser-session, or unrelated service credentials.

The destructive PITR drill is allowed only on disposable qualification PostgreSQL data. The script additionally requires `ALLOW_DESTRUCTIVE_PITR_DRILL=true`.

## 3. Execute repository qualification

Use workflow `live-pilot-qualification` on branch `feat/p0c-live-pilot-qualification`.

First run with both optional external/destructive inputs disabled. The repository qualification job must be PASS.

Expected internal gates already covered by ordinary CI:

- PostgreSQL migrations
- DB-backed kill switches
- restart-safe reconciliation
- Python compile
- Rego compile
- OpenBao policy/bootstrap syntax
- Compose validation
- application image build

## 4. Execute Meta + Stripe TEST E2E

Dispatch `live-pilot-qualification` with:

`run_external_test = true`

The environment reviewer must approve access to protected TEST secrets.

Meta PASS requires actual TEST publication confirmation through the official adapter. Stripe PASS requires a TEST account plus evidence that signed webhook verification, receipt deduplication, idempotent fulfillment, and settlement reconciliation are all true.

Any `NOT_RUN`, timeout, unknown response, invalid credential, live credential, missing evidence, or provider ambiguity is NO_GO.

## 5. Execute PostgreSQL PITR drill

Dispatch the same workflow with:

`run_pitr_drill = true`

The job must execute only on the `live-pilot-qualifier` runner. The restore target must be disposable and separate from the source cluster.

PASS requires retained evidence that a PostgreSQL 18 base backup and WAL recovery can restore the qualification database to the requested recovery point and that application invariants/ledger data are intact after recovery.

## 6. OpenBao production-identity evidence and signed bundle

The qualification identity must authenticate to OpenBao without a static production secret stored in the repository. The token supplied to the workflow must be short-lived and constrained by the Transit signing policy.

`scripts/sign_evidence.py` signs the evidence bundle through OpenBao Transit. The private signing key must never leave OpenBao.

Retain the signed bundle as a GitHub Actions artifact and record its digest in the readiness evidence.

## 7. Deterministic readiness evaluation

Run the readiness evaluator only against retained evidence from the exact qualification commit.

A candidate can reach `LIVE_PILOT_READY` only when every mandatory gate is exactly `PASS`, including:

- repository qualification
- DB-backed kill switches
- restart/crash reconciliation
- Meta TEST E2E
- Stripe TEST E2E
- PostgreSQL PITR/restore
- OpenBao workload identity
- signed evidence bundle
- observability/SLO evidence required by the manifest
- explicit human go-live approval

Missing, partial, unknown, stale, unsigned, or mismatched-commit evidence is `NO_GO`.

## 8. Promotion boundary

Even when the evaluator returns `LIVE_PILOT_READY`, it must not automatically enable external execution. Promotion is a separate human-authorized change with its own commit/evidence and the smallest possible pilot scope.
