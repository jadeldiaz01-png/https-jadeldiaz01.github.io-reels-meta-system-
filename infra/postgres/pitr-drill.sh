#!/usr/bin/env bash
set -euo pipefail

: "${PGDATA_SOURCE:?PGDATA_SOURCE required}"
: "${PG_BASEBACKUP_DIR:?PG_BASEBACKUP_DIR required}"
: "${PG_RESTORE_DIR:?PG_RESTORE_DIR required}"
: "${WAL_ARCHIVE_DIR:?WAL_ARCHIVE_DIR required}"
: "${PGHOST:?PGHOST required}"
: "${PGUSER:?PGUSER required}"
: "${PGPORT:=5432}"
: "${RECOVERY_TARGET_TIME:?RECOVERY_TARGET_TIME required}"

if [[ "${ALLOW_DESTRUCTIVE_PITR_DRILL:-false}" != "true" ]]; then
  echo "Refusing destructive PITR drill without ALLOW_DESTRUCTIVE_PITR_DRILL=true" >&2
  exit 2
fi

rm -rf "$PG_BASEBACKUP_DIR" "$PG_RESTORE_DIR"
mkdir -p "$PG_BASEBACKUP_DIR" "$PG_RESTORE_DIR" "$WAL_ARCHIVE_DIR"

# This requires archive_mode=on and a functioning archive_command before the base backup.
pg_basebackup -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -D "$PG_BASEBACKUP_DIR" -Fp -Xs -P
cp -a "$PG_BASEBACKUP_DIR"/. "$PG_RESTORE_DIR"/
cat >> "$PG_RESTORE_DIR/postgresql.auto.conf" <<EOF
restore_command = 'cp ${WAL_ARCHIVE_DIR}/%f %p'
recovery_target_time = '${RECOVERY_TARGET_TIME}'
recovery_target_action = 'promote'
EOF
touch "$PG_RESTORE_DIR/recovery.signal"

python - <<'PY'
import hashlib, json, os, pathlib, time
root = pathlib.Path(os.environ['PG_BASEBACKUP_DIR'])
h = hashlib.sha256()
for path in sorted(p for p in root.rglob('*') if p.is_file()):
    h.update(str(path.relative_to(root)).encode())
    h.update(path.read_bytes())
print(json.dumps({
    'gate': 'backup_restore_pitr',
    'status': 'PREPARED_FOR_ISOLATED_RESTORE',
    'base_backup_sha256': h.hexdigest(),
    'recovery_target_time': os.environ['RECOVERY_TARGET_TIME'],
    'recorded_at_epoch': int(time.time()),
}, sort_keys=True))
PY

echo "Start an isolated PostgreSQL 18 instance with PGDATA=$PG_RESTORE_DIR, then verify target rows and timeline before recording PASS."
