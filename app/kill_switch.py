from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text

from app.models import ExternalActionIntent


@dataclass(frozen=True)
class KillDecision:
    blocked: bool
    scope: str | None = None
    scope_key: str | None = None
    reason: str | None = None


class KillSwitchStore:
    """PostgreSQL-backed kill switches. Any database error fails closed."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def set(self, scope: str, scope_key: str, *, enabled: bool, reason: str, actor: str) -> None:
        if scope not in {"global", "platform", "account", "action_class"}:
            raise ValueError("invalid_kill_switch_scope")
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO kill_switches(scope,scope_key,enabled,reason,changed_by,changed_at)
                VALUES (:scope,:key,:enabled,:reason,:actor,now())
                ON CONFLICT(scope,scope_key) DO UPDATE
                SET enabled=EXCLUDED.enabled, reason=EXCLUDED.reason,
                    changed_by=EXCLUDED.changed_by, changed_at=now()
            """), {"scope": scope, "key": scope_key, "enabled": enabled, "reason": reason, "actor": actor})

    def evaluate(self, intent: ExternalActionIntent) -> KillDecision:
        account = str(intent.payload.get("account_id", ""))
        checks = [
            ("global", "*"),
            ("platform", intent.target),
            ("action_class", intent.action_class.value),
        ]
        if account:
            checks.insert(2, ("account", account))
        try:
            with self.engine.connect() as conn:
                for scope, key in checks:
                    row = conn.execute(text("""
                        SELECT enabled, reason FROM kill_switches
                        WHERE scope=:scope AND scope_key=:key
                    """), {"scope": scope, "key": key}).mappings().first()
                    if row and row["enabled"]:
                        return KillDecision(True, scope, key, row["reason"])
        except Exception as exc:
            return KillDecision(True, "database", "unavailable", type(exc).__name__)
        return KillDecision(False)
