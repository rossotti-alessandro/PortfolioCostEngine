"""SQLite persistence (SQLAlchemy 2). Every prospect-scoped row carries tenant_id and
every query in the API filters by it. Raw documents are immutable: identified by SHA-256,
never overwritten; corrections live in fact values + review rows, originals are kept."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class Prospect(Base):
    __tablename__ = "prospect"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(200))
    domicile: Mapped[str] = mapped_column(String(2), default="CH")
    base_ccy: Mapped[str] = mapped_column(String(3), default="CHF")
    synthetic: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(32), default=now)
    proposal: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class Document(Base):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospect.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(40))
    doc_type_override: Mapped[str | None] = mapped_column(String(40), nullable=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    pages: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="extracted")
    extractor_version: Mapped[str] = mapped_column(String(40), default="")
    uploaded_at: Mapped[str] = mapped_column(String(32), default=now)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="analyst")
    __table_args__ = (UniqueConstraint("tenant_id", "prospect_id", "sha256"),)


class FactRow(Base):
    __tablename__ = "fact"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), index=True)
    key: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))
    field: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(Text)
    value_extracted: Mapped[str | None] = mapped_column(String(60), nullable=True)
    value_current: Mapped[str | None] = mapped_column(String(60), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    fee_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    measurement: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="extracted")  # extracted|accepted|corrected|rejected|manual


class Review(Base):
    __tablename__ = "review"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    fact_id: Mapped[int] = mapped_column(ForeignKey("fact.id"), index=True)
    action: Mapped[str] = mapped_column(String(20))
    old_value: Mapped[str | None] = mapped_column(String(60), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[str] = mapped_column(String(100))
    at: Mapped[str] = mapped_column(String(32), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    at: Mapped[str] = mapped_column(String(32), default=now)
    user: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class RequestState(Base):
    __tablename__ = "request_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(Integer, index=True)
    key: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))  # open|sent|waived
    updated_at: Mapped[str] = mapped_column(String(32), default=now)
    __table_args__ = (UniqueConstraint("tenant_id", "prospect_id", "key"),)


class ProposalVersion(Base):
    __tablename__ = "proposal_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(Integer, index=True)
    version: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSON)
    user: Mapped[str] = mapped_column(String(100))
    at: Mapped[str] = mapped_column(String(32), default=now)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class Approval(Base):
    __tablename__ = "approval"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(Integer, index=True)
    user: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(40))
    at: Mapped[str] = mapped_column(String(32), default=now)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, default="")


def data_dir() -> Path:
    d = Path(os.environ.get("PCE_DATA_DIR", Path(__file__).resolve().parents[3] / "var"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_session_factory(url: str | None = None):
    url = url or os.environ.get("PCE_DATABASE_URL") or f"sqlite:///{data_dir() / 'pce.sqlite'}"
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
                           json_serializer=lambda o: json.dumps(o, default=str))
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
