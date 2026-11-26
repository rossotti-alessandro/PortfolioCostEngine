"""Erase a prospect and everything derived from it (SC-11.11), on request or when retention ends.

Removes the prospect, its documents and stored files, extracted facts, reviews, proposals, approvals,
document requests and its activity-log entries (they can name files and values), and unlinks or deletes the
CRM contact with its notes and stage history. What stays is one ``prospect.erased`` entry with a fixed
reason, counts and the ids of the removed log entries, so the firm can prove it erased the data without
keeping any of it, and the tamper check (``pce.audit``) knows those gaps were made by the application.
Backups still hold the data until they expire.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from . import audit
from .crm.models import Activity, Contact, StageEvent
from .db import (
    Account,
    Approval,
    AuditEvent,
    AuditSeal,
    Document,
    FactRow,
    Position,
    ProposalVersion,
    Prospect,
    RequestState,
    Review,
    Transaction,
)

# A fixed list, not free text: the reason is kept after the deletion and must not carry personal data.
Reason = Literal["prospect_request", "no_mandate", "retention_expired", "uploaded_by_mistake"]


def erase_prospect(
    db: Session, tenant: str, pid: int, user: str, reason: Reason, erase_contact: bool
) -> dict:
    """Delete one prospect of ``tenant``. Commits. Returns counts for the log entry and the caller."""
    p = db.scalar(select(Prospect).where(Prospect.id == pid, Prospect.tenant_id == tenant))
    if p is None:
        raise LookupError("prospect not found")
    docs = db.scalars(select(Document).where(Document.prospect_id == pid, Document.tenant_id == tenant)).all()
    doc_ids = [d.id for d in docs]
    fact_ids = list(db.scalars(select(FactRow.id).where(FactRow.document_id.in_(doc_ids)))) if doc_ids else []
    counts: dict[str, int] = {"documents": len(doc_ids), "facts": len(fact_ids)}
    # derived book of record first: its rows point at facts and the prospect
    for model in (Transaction, Position, Account):
        db.execute(delete(model).where(model.prospect_id == pid, model.tenant_id == tenant))
    if fact_ids:
        counts["reviews"] = db.execute(delete(Review).where(Review.fact_id.in_(fact_ids))).rowcount or 0
        db.execute(delete(FactRow).where(FactRow.id.in_(fact_ids)))
    for model in (RequestState, ProposalVersion, Approval):
        db.execute(delete(model).where(model.prospect_id == pid, model.tenant_id == tenant))
    log_ids = list(
        db.scalars(select(AuditEvent.id).where(AuditEvent.prospect_id == pid, AuditEvent.tenant_id == tenant))
    )
    if log_ids:
        db.execute(delete(AuditSeal).where(AuditSeal.event_id.in_(log_ids)))
        db.execute(delete(AuditEvent).where(AuditEvent.id.in_(log_ids)))
    contacts = list(
        db.scalars(select(Contact.id).where(Contact.prospect_id == pid, Contact.tenant_id == tenant))
    )
    if erase_contact and contacts:
        db.execute(delete(StageEvent).where(StageEvent.contact_id.in_(contacts)))
        db.execute(delete(Activity).where(Activity.contact_id.in_(contacts)))
        db.execute(delete(Contact).where(Contact.id.in_(contacts)))
    elif contacts:
        db.execute(update(Contact).where(Contact.id.in_(contacts)).values(prospect_id=None))
    counts["contacts_deleted" if erase_contact else "contacts_unlinked"] = len(contacts)
    paths = {d.storage_path for d in docs}
    for d in docs:
        db.delete(d)
    db.delete(p)
    db.flush()
    # A file is stored once per tenant by content hash: keep it if another prospect still uses it.
    still_used = set(db.scalars(select(Document.storage_path).where(Document.storage_path.in_(paths))))
    for path in paths - still_used:
        Path(path).unlink(missing_ok=True)
    counts["files_removed"] = len(paths - still_used)
    # prospect_id None: the prospect is gone; the entry must not point to or name it.
    audit.record(db, tenant, user, "prospect.erased", reason=reason, log_entries=log_ids, **counts)
    db.commit()
    return counts
