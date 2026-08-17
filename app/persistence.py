from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.models import ActionClass, ExternalActionIntent, IntentState


class Base(DeclarativeBase):
    pass


class IntentRow(Base):
    __tablename__ = "external_action_intents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    action_class: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    external_id: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EvidenceRow(Base):
    __tablename__ = "evidence_ledger"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intent_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(Text)
    event_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IntentRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def save(self, intent: ExternalActionIntent) -> ExternalActionIntent:
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session, session.begin():
            row = session.scalar(select(IntentRow).where(IntentRow.idempotency_key == intent.idempotency_key))
            if row is None:
                row = IntentRow(id=intent.id, idempotency_key=intent.idempotency_key, action_class=intent.action_class.value,
                                target=intent.target, payload=intent.payload, state=intent.state.value,
                                approved=intent.approved, external_id=intent.external_id, attempt=intent.attempt,
                                created_at=now, updated_at=now)
                session.add(row)
            else:
                row.payload = intent.payload
                row.state = intent.state.value
                row.approved = intent.approved
                row.external_id = intent.external_id
                row.attempt = intent.attempt
                row.updated_at = now
        return intent

    def get_by_key(self, idempotency_key: str) -> ExternalActionIntent | None:
        with Session(self.engine) as session:
            row = session.scalar(select(IntentRow).where(IntentRow.idempotency_key == idempotency_key))
            if row is None:
                return None
            return ExternalActionIntent(id=row.id, idempotency_key=row.idempotency_key,
                action_class=ActionClass(row.action_class), target=row.target, payload=row.payload,
                state=IntentState(row.state), approved=row.approved, external_id=row.external_id, attempt=row.attempt)


class EvidenceLedger:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def append(self, event_type: str, payload: dict, intent_id: UUID | None = None) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        with Session(self.engine) as session, session.begin():
            previous = session.scalar(select(EvidenceRow.event_hash).order_by(EvidenceRow.id.desc()).limit(1))
            event_hash = hashlib.sha256(f"{previous or ''}|{event_type}|{canonical}".encode()).hexdigest()
            session.add(EvidenceRow(intent_id=intent_id, event_type=event_type, payload=payload,
                                    previous_hash=previous, event_hash=event_hash))
        return event_hash
