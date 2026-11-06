"""CRM API under ``/api/crm``. Tenant-scoped through the same header context as the rest of the API.

Nothing here reads or returns internal economics (margin, revenue): the CRM is shown to anyone in the
firm and its payloads must stay free of them (tested).
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import AuditEvent, Prospect, now
from .funnel import compute_funnel
from .models import (
    ACTIVITY_KINDS,
    KINDS,
    LOST_REASONS,
    OPEN_STAGES,
    SOURCES,
    STAGE_LABELS,
    STAGES,
    Activity,
    Contact,
    StageEvent,
)

router = APIRouter(prefix="/api/crm", tags=["crm"])


# pce.api includes this router, so its dependencies are resolved lazily to avoid an import cycle.
def _db():
    from ..api import get_db

    yield from get_db()


def _ctx(
    x_tenant_id: Annotated[str, Header()] = "demo-firm",
    x_user: Annotated[str, Header()] = "analyst",
    x_role: Annotated[str, Header()] = "analyst",
):
    from ..api import ctx

    return ctx(x_tenant_id, x_user, x_role)


DB = Annotated[Session, Depends(_db)]
C = Annotated[Any, Depends(_ctx)]

Stage = Literal["lead", "qualified", "documents_received", "cost_review", "proposal_sent", "won", "lost"]


def _check_aum(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    try:
        d = Decimal(v)
    except InvalidOperation as e:
        raise ValueError("estimated_aum must be a decimal number") from e
    if d < 0:
        raise ValueError("estimated_aum must not be negative")
    return str(d)


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["individual", "family", "company", "foundation"] = "individual"
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=50)
    domicile: str = Field(default="CH", min_length=2, max_length=2)
    source: Literal["referral", "intermediary", "event", "website", "network", "other"] = "other"
    owner: str | None = Field(default=None, max_length=100)
    estimated_aum: str | None = None
    currency: str = Field(default="CHF", min_length=3, max_length=3)
    current_banks: list[str] = Field(default_factory=list, max_length=20)
    stage: Literal["lead", "qualified", "documents_received", "cost_review", "proposal_sent"] = "lead"
    next_action: str = Field(default="", max_length=500)
    next_action_due: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: str = Field(default="", max_length=5000)

    _aum = field_validator("estimated_aum")(_check_aum)


class ContactPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: Literal["individual", "family", "company", "foundation"] | None = None
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    domicile: str | None = Field(default=None, min_length=2, max_length=2)
    source: Literal["referral", "intermediary", "event", "website", "network", "other"] | None = None
    owner: str | None = Field(default=None, max_length=100)
    estimated_aum: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    current_banks: list[str] | None = Field(default=None, max_length=20)
    next_action: str | None = Field(default=None, max_length=500)
    next_action_due: str | None = Field(default=None, pattern=r"^(\d{4}-\d{2}-\d{2})?$")
    notes: str | None = Field(default=None, max_length=5000)

    _aum = field_validator("estimated_aum")(_check_aum)


class StageMove(BaseModel):
    to_stage: Stage
    note: str = Field(default="", max_length=1000)
    lost_reason: Literal[tuple(LOST_REASONS)] | None = None  # type: ignore[valid-type]


class ActivityIn(BaseModel):
    kind: Literal[ACTIVITY_KINDS] = "note"  # type: ignore[valid-type]
    summary: str = Field(min_length=1, max_length=2000)


class CostReviewLink(BaseModel):
    prospect_id: int | None = None  # link an existing cost review; None creates a new one


def audit(db: Session, c: Any, action: str, contact_id: int, prospect_id: int | None = None, **detail: Any):
    db.add(
        AuditEvent(
            tenant_id=c.tenant,
            prospect_id=prospect_id,
            user=c.user,
            action=action,
            detail={"contact_id": contact_id, **detail},
        )
    )


def get_contact(db: Session, c: Any, cid: int) -> Contact:
    k = db.scalar(select(Contact).where(Contact.id == cid, Contact.tenant_id == c.tenant))
    if not k:
        raise HTTPException(404, "contact not found")  # same answer for other tenants
    return k


def lifecycle(stage: str) -> str:
    return "client" if stage == "won" else "lost" if stage == "lost" else "prospect"


def contact_out(k: Contact, prospect_code: str | None = None) -> dict:
    return {
        "id": k.id,
        "name": k.name,
        "kind": k.kind,
        "email": k.email,
        "phone": k.phone,
        "domicile": k.domicile,
        "source": k.source,
        "owner": k.owner,
        "estimated_aum": k.estimated_aum,
        "currency": k.currency,
        "current_banks": k.current_banks,
        "stage": k.stage,
        "stage_label": STAGE_LABELS[k.stage],
        "lifecycle": lifecycle(k.stage),
        "lost_reason": k.lost_reason,
        "next_action": k.next_action,
        "next_action_due": k.next_action_due,
        "notes": k.notes,
        "prospect": {"id": k.prospect_id, "code": prospect_code} if k.prospect_id else None,
        "synthetic": k.synthetic,
        "created_at": k.created_at,
        "updated_at": k.updated_at,
    }


def _prospect_codes(db: Session, c: Any, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.execute(
        select(Prospect.id, Prospect.code).where(Prospect.tenant_id == c.tenant, Prospect.id.in_(ids))
    )
    return {pid: code for pid, code in rows}


def move(db: Session, c: Any, k: Contact, to: str, note: str = "", at: str | None = None) -> None:
    at = at or now()
    db.add(
        StageEvent(
            tenant_id=c.tenant,
            contact_id=k.id,
            from_stage=k.stage,
            to_stage=to,
            at=at,
            user=c.user,
            note=note,
        )
    )
    k.stage = to
    k.updated_at = at


@router.get("/meta")
def meta() -> dict:
    return {
        "stages": [{"id": s, "label": STAGE_LABELS[s], "open": s in OPEN_STAGES} for s in STAGES],
        "lost_reasons": [{"id": k, "label": v} for k, v in LOST_REASONS.items()],
        "sources": [{"id": k, "label": v} for k, v in SOURCES.items()],
        "kinds": [{"id": k, "label": v} for k, v in KINDS.items()],
        "activity_kinds": list(ACTIVITY_KINDS),
    }


@router.get("/contacts")
def list_contacts(
    db: DB,
    c: C,
    stage: Stage | None = None,
    lifecycle_: Annotated[Literal["prospect", "client", "lost"] | None, Query(alias="lifecycle")] = None,
    q: str | None = None,
    owner: str | None = None,
) -> list[dict]:
    stmt = select(Contact).where(Contact.tenant_id == c.tenant)
    if stage:
        stmt = stmt.where(Contact.stage == stage)
    if lifecycle_ == "client":
        stmt = stmt.where(Contact.stage == "won")
    elif lifecycle_ == "lost":
        stmt = stmt.where(Contact.stage == "lost")
    elif lifecycle_ == "prospect":
        stmt = stmt.where(Contact.stage.in_(OPEN_STAGES))
    if owner:
        stmt = stmt.where(Contact.owner == owner)
    if q:
        stmt = stmt.where(Contact.name.ilike(f"%{q}%"))
    rows = db.scalars(stmt.order_by(Contact.updated_at.desc(), Contact.id.desc())).all()
    codes = _prospect_codes(db, c, {k.prospect_id for k in rows if k.prospect_id})
    return [contact_out(k, codes.get(k.prospect_id or 0)) for k in rows]


@router.post("/contacts", status_code=201)
def create_contact(body: ContactIn, db: DB, c: C) -> dict:
    data = body.model_dump()
    stage = data.pop("stage")
    data["domicile"] = data["domicile"].upper()
    data["currency"] = data["currency"].upper()
    data["owner"] = data["owner"] or c.user
    k = Contact(tenant_id=c.tenant, stage=stage, **data)
    db.add(k)
    db.flush()
    db.add(
        StageEvent(
            tenant_id=c.tenant, contact_id=k.id, from_stage=None, to_stage=stage, at=k.created_at, user=c.user
        )
    )
    audit(db, c, "crm.contact.created", k.id, stage=stage)
    db.commit()
    return contact_out(k)


@router.get("/contacts/{cid}")
def get_one(cid: int, db: DB, c: C) -> dict:
    k = get_contact(db, c, cid)
    codes = _prospect_codes(db, c, {k.prospect_id} if k.prospect_id else set())
    events = db.scalars(
        select(StageEvent)
        .where(StageEvent.contact_id == k.id, StageEvent.tenant_id == c.tenant)
        .order_by(StageEvent.at, StageEvent.id)
    ).all()
    acts = db.scalars(
        select(Activity)
        .where(Activity.contact_id == k.id, Activity.tenant_id == c.tenant)
        .order_by(Activity.at.desc(), Activity.id.desc())
    ).all()
    return {
        **contact_out(k, codes.get(k.prospect_id or 0)),
        "history": [
            {
                "from_stage": e.from_stage,
                "to_stage": e.to_stage,
                "to_label": STAGE_LABELS[e.to_stage],
                "at": e.at,
                "user": e.user,
                "note": e.note,
            }
            for e in events
        ],
        "activities": [
            {"id": a.id, "kind": a.kind, "summary": a.summary, "at": a.at, "user": a.user} for a in acts
        ],
    }


@router.patch("/contacts/{cid}")
def patch_contact(cid: int, body: ContactPatch, db: DB, c: C) -> dict:
    k = get_contact(db, c, cid)
    changes = body.model_dump(exclude_unset=True)
    for f in ("domicile", "currency"):
        if changes.get(f):
            changes[f] = changes[f].upper()
    if changes.get("next_action_due") == "":
        changes["next_action_due"] = None
    for f, v in changes.items():
        setattr(k, f, v)
    k.updated_at = now()
    audit(db, c, "crm.contact.updated", k.id, fields=sorted(changes))
    db.commit()
    return get_one(cid, db, c)


@router.post("/contacts/{cid}/stage")
def move_stage(cid: int, body: StageMove, db: DB, c: C) -> dict:
    k = get_contact(db, c, cid)
    if body.to_stage == k.stage:
        raise HTTPException(409, "contact is already in this stage")
    if body.to_stage == "lost" and not body.lost_reason:
        raise HTTPException(422, "a lost reason is required")
    before = k.stage
    move(db, c, k, body.to_stage, body.note)
    k.lost_reason = body.lost_reason if body.to_stage == "lost" else None
    audit(db, c, "crm.stage.moved", k.id, k.prospect_id, from_stage=before, to_stage=k.stage)
    db.commit()
    return get_one(cid, db, c)


@router.post("/contacts/{cid}/activities", status_code=201)
def add_activity(cid: int, body: ActivityIn, db: DB, c: C) -> dict:
    k = get_contact(db, c, cid)
    a = Activity(tenant_id=c.tenant, contact_id=k.id, kind=body.kind, summary=body.summary, user=c.user)
    db.add(a)
    k.updated_at = now()
    db.commit()
    return {"id": a.id, "kind": a.kind, "summary": a.summary, "at": a.at, "user": a.user}


@router.post("/contacts/{cid}/cost-review")
def link_cost_review(cid: int, body: CostReviewLink, db: DB, c: C) -> dict:
    """Link the contact to a cost review (FeeLens prospect), creating one if no id is given."""
    from ..demo import spec

    k = get_contact(db, c, cid)
    if body.prospect_id is not None:
        p = db.scalar(select(Prospect).where(Prospect.id == body.prospect_id, Prospect.tenant_id == c.tenant))
        if not p:
            raise HTTPException(404, "prospect not found")
    else:
        code = f"CRM-{k.id}"
        p = db.scalar(select(Prospect).where(Prospect.tenant_id == c.tenant, Prospect.code == code))
        if not p:
            p = Prospect(
                tenant_id=c.tenant,
                code=code,
                label=k.name,
                domicile=k.domicile,
                synthetic=k.synthetic,
                proposal=json.loads(json.dumps(spec.PROPOSAL_DEFAULTS)),
            )
            db.add(p)
            db.flush()
            db.add(
                AuditEvent(
                    tenant_id=c.tenant,
                    prospect_id=p.id,
                    user=c.user,
                    action="prospect.created",
                    detail={"code": code, "from_contact": k.id},
                )
            )
    k.prospect_id = p.id
    k.updated_at = now()
    audit(db, c, "crm.cost_review.linked", k.id, p.id)
    db.commit()
    return get_one(cid, db, c)


@router.get("/funnel")
def funnel(
    db: DB,
    c: C,
    since: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    until: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    owner: str | None = None,
    source: str | None = None,
) -> dict:
    """Funnel for the cohort of contacts created in [since, until] (inclusive dates)."""
    stmt = select(Contact).where(Contact.tenant_id == c.tenant)
    if since:
        stmt = stmt.where(Contact.created_at >= since)
    if until:
        stmt = stmt.where(Contact.created_at < until + "T99")  # inclusive of the whole day
    if owner:
        stmt = stmt.where(Contact.owner == owner)
    if source:
        stmt = stmt.where(Contact.source == source)
    contacts = db.scalars(stmt).all()
    ids = [k.id for k in contacts]
    events = (
        db.scalars(
            select(StageEvent).where(StageEvent.tenant_id == c.tenant, StageEvent.contact_id.in_(ids))
        ).all()
        if ids
        else []
    )
    owners = sorted(set(db.scalars(select(Contact.owner).where(Contact.tenant_id == c.tenant)).all()))
    result = compute_funnel(
        [
            {
                "id": k.id,
                "stage": k.stage,
                "created_at": k.created_at,
                "estimated_aum": k.estimated_aum,
                "currency": k.currency,
                "source": k.source,
                "lost_reason": k.lost_reason,
            }
            for k in contacts
        ],
        [{"id": e.id, "contact_id": e.contact_id, "to_stage": e.to_stage, "at": e.at} for e in events],
    )
    return {
        **result,
        "filters": {"since": since, "until": until, "owner": owner, "source": source},
        "owners": owners,
        "synthetic": any(k.synthetic for k in contacts),
    }


@router.post("/demo/seed")
def seed(db: DB, c: C) -> dict:
    """Create the SYNTHETIC CRM book (idempotent per tenant)."""
    from .seed import seed_contacts

    return {"contacts_added": seed_contacts(db, c, move)}
