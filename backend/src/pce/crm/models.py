"""CRM tables. Same ``Base`` and database as the rest of the app; every row carries ``tenant_id``.

Stage changes are append-only ``crm_stage_event`` rows, so the funnel is computed from history:
a contact that reached "Proposal sent" and was then lost still counts as having reached it.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, now

# Ordered pipeline. "won" closes it; "lost" can happen from any open stage.
OPEN_STAGES = ("lead", "qualified", "documents_received", "cost_review", "proposal_sent")
STAGES = (*OPEN_STAGES, "won", "lost")
FUNNEL_STAGES = (*OPEN_STAGES, "won")
STAGE_LABELS = {
    "lead": "Lead",
    "qualified": "Qualified",
    "documents_received": "Documents received",
    "cost_review": "Cost review",
    "proposal_sent": "Proposal sent",
    "won": "Won (client)",
    "lost": "Lost",
}
LOST_REASONS = {
    "stayed_with_bank": "Stayed with current bank",
    "price": "Price",
    "no_saving": "No meaningful saving",
    "timing": "Timing / not now",
    "chose_competitor": "Chose another manager",
    "no_response": "No response",
    "other": "Other",
}
SOURCES = {
    "referral": "Client referral",
    "intermediary": "Lawyer / fiduciary",
    "event": "Event",
    "website": "Website",
    "network": "Personal network",
    "other": "Other",
}
KINDS = {
    "individual": "Individual",
    "family": "Family",
    "company": "Company",
    "foundation": "Foundation / trust",
}
ACTIVITY_KINDS = ("note", "call", "meeting", "email")


class Contact(Base):
    __tablename__ = "crm_contact"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="individual")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    domicile: Mapped[str] = mapped_column(String(2), default="CH")
    source: Mapped[str] = mapped_column(String(20), default="other")
    owner: Mapped[str] = mapped_column(String(100))
    estimated_aum: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # Decimal string; None = unknown
    currency: Mapped[str] = mapped_column(String(3), default="CHF")
    current_banks: Mapped[list] = mapped_column(default=list)
    stage: Mapped[str] = mapped_column(String(30), default="lead")
    lost_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    next_action: Mapped[str] = mapped_column(Text, default="")
    next_action_due: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    prospect_id: Mapped[int | None] = mapped_column(ForeignKey("prospect.id"), nullable=True)
    synthetic: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String(32), default=now)
    updated_at: Mapped[str] = mapped_column(String(32), default=now)


class StageEvent(Base):
    __tablename__ = "crm_stage_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("crm_contact.id"), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(30))
    at: Mapped[str] = mapped_column(String(32), default=now)
    user: Mapped[str] = mapped_column(String(100))
    note: Mapped[str] = mapped_column(Text, default="")


class Activity(Base):
    __tablename__ = "crm_activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("crm_contact.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)
    at: Mapped[str] = mapped_column(String(32), default=now)
    user: Mapped[str] = mapped_column(String(100))
