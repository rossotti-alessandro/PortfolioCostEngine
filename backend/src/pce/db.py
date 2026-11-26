"""SQLite persistence (SQLAlchemy 2). Every prospect-scoped row carries tenant_id and
every query in the API filters by it. Raw documents are immutable: identified by SHA-256,
never overwritten; corrections live in fact values + review rows, originals are kept."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Base(DeclarativeBase):
    type_annotation_map: ClassVar = {dict: JSON, list: JSON}


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
    status: Mapped[str] = mapped_column(
        String(20), default="extracted"
    )  # extracted|accepted|corrected|rejected|manual


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


class AuditSeal(Base):
    """HMAC of one audit_event row (SC-11.8). A changed, deleted or hand-inserted event fails the check."""

    __tablename__ = "audit_seal"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key_id: Mapped[str] = mapped_column(String(16))
    mac: Mapped[str] = mapped_column(String(64))


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


class UserAccount(Base):
    """A named person (SC-11.12). The env admin is not stored here: it is the break-glass account."""

    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)  # global: sign-in has no tenant field
    display_name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(300))
    roles: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(default=True)
    must_change_password: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(String(32), default=now)
    created_by: Mapped[str] = mapped_column(String(100), default="")


class UserMfa(Base):
    """A named person's authenticator-app key (TOTP, SC-11.7). Own table: user_account needs no migration."""

    __tablename__ = "user_mfa"
    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    secret: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(32), default=now)


class AuthSession(Base):
    """Server-side record of a sign-in, so sign-out, idle timeout and revocation take effect at once."""

    __tablename__ = "auth_session"
    sid: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[float] = mapped_column()
    last_seen: Mapped[float] = mapped_column()
    expires_at: Mapped[float] = mapped_column()
    revoked: Mapped[bool] = mapped_column(default=False)


# Book of record (SC-7.12): the family's accounts and dated positions as rows, so costs can attach to real
# objects. Rebuilt from the analysis on every compute, so it is derived data: deleting it loses nothing.
class Account(Base):
    """One booking relationship: a prospect's holdings at one institution."""

    __tablename__ = "account"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospect.id"), index=True)
    institution: Mapped[str] = mapped_column(String(200))
    jurisdiction: Mapped[str | None] = mapped_column(String(2), nullable=True)
    __table_args__ = (UniqueConstraint("tenant_id", "prospect_id", "institution"),)


class Instrument(Base):
    """Public reference data, keyed by ISIN and shared across tenants. Never holds client data: no
    quantity, value or account, only what a public register would say about the security."""

    __tablename__ = "instrument"
    isin: Mapped[str] = mapped_column(String(12), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    asset_class: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class Position(Base):
    """One line of a statement of assets, at the statement date."""

    __tablename__ = "position"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospect.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), index=True)
    isin: Mapped[str | None] = mapped_column(ForeignKey("instrument.isin"), nullable=True)
    name: Mapped[str] = mapped_column(Text)
    asset_class: Mapped[str] = mapped_column(String(20))
    as_of: Mapped[str | None] = mapped_column(String(10), nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    value_ccy: Mapped[str] = mapped_column(String(40))  # Decimal as string, in the position's currency
    value_base: Mapped[str | None] = mapped_column(String(40), nullable=True)  # None: no printed FX rate
    fact_id: Mapped[int] = mapped_column(Integer)  # no FK: re-parsing replaces facts, then this row
    __table_args__ = (UniqueConstraint("tenant_id", "fact_id"),)


class Transaction(Base):
    """One trade or FX conversion from a transaction list (SC-7.18): the turnover trading costs scale with."""

    __tablename__ = "transaction"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospect.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), index=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)  # None for an FX conversion
    booking_date: Mapped[str] = mapped_column(String(10))
    side: Mapped[str] = mapped_column(String(8))  # buy | sell | fx
    quantity: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # None: not printed or not consistent
    currency: Mapped[str] = mapped_column(String(3))
    gross_ccy: Mapped[str] = mapped_column(String(40))  # Decimal as string, in ``currency``
    fact_id: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("tenant_id", "fact_id"),)


def data_dir() -> Path:
    d = Path(os.environ.get("PCE_DATA_DIR", Path(__file__).resolve().parents[3] / "var"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_session_factory(url: str | None = None):
    url = url or os.environ.get("PCE_DATABASE_URL") or f"sqlite:///{data_dir() / 'pce.sqlite'}"
    engine = create_engine(
        url,
        # timeout: a writer waits up to 30 s for SQLite's single write lock instead of failing after 5 s.
        connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {},
        json_serializer=lambda o: json.dumps(o, default=str),
    )
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
