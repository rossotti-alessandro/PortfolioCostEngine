"""Erase a prospect and everything derived from it (SC-11.11), on request or when retention ends (SC-11.6).

Removes the prospect, its documents and stored files, extracted facts, reviews, proposals, approvals,
document requests and earlier audit entries (they can name files and values), and unlinks or deletes the
CRM contact. What stays is one audit entry that says a deletion happened, with counts only, so the firm can
prove it erased the data without keeping any of it. Backups still hold the data until they expire
(docs/app/PILOT_INSTALL.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .crm.models import Contact, StageEvent
from .db import (
    Approval,
    AuditEvent,
    Document,
    FactRow,
    ProposalVersion,
    Prospect,
    RequestState,
    Review,
)

# A fixed list, not free text: the reason is kept after the deletion and must not carry personal data.
Reason = Literal["prospect_request", "no_mandate", "retention_expired", "uploaded_by_mistake"]


def erase_prospect(
    db: Session, tenant: str, pid: int, user: str, reason: Reason, erase_contact: bool
) -> dict:
    """Delete one prospect of ``tenant``. Commits. Returns counts for the audit entry and the caller."""
    p = db.scalar(select(Prospect).where(Prospect.id == pid, Prospect.tenant_id == tenant))
    if p is None:
        raise LookupError("prospect not found")
    docs = db.scalars(select(Document).where(Document.prospect_id == pid, Document.tenant_id == tenant)).all()
    doc_ids = [d.id for d in docs]
    fact_ids = list(db.scalars(select(FactRow.id).where(FactRow.document_id.in_(doc_ids)))) if doc_ids else []
    counts = {"documents": len(doc_ids), "facts": len(fact_ids)}
    if fact_ids:
        counts["reviews"] = db.execute(delete(Review).where(Review.fact_id.in_(fact_ids))).rowcount
        db.execute(delete(FactRow).where(FactRow.id.in_(fact_ids)))
    for model in (RequestState, ProposalVersion, Approval, AuditEvent):
        db.execute(delete(model).where(model.prospect_id == pid, model.tenant_id == tenant))
    contacts = list(
        db.scalars(select(Contact.id).where(Contact.prospect_id == pid, Contact.tenant_id == tenant))
    )
    if erase_contact and contacts:
        db.execute(delete(StageEvent).where(StageEvent.contact_id.in_(contacts)))
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
    removed = 0
    for path in paths - still_used:
        Path(path).unlink(missing_ok=True)
        removed += 1
    counts["files_removed"] = removed
    db.add(
        AuditEvent(
            tenant_id=tenant,
            prospect_id=None,  # the prospect is gone; the entry must not point to or name it
            user=user,
            action="prospect.erased",
            detail={"reason": reason, **counts},
        )
    )
    db.commit()
    return counts
