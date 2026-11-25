"""Tamper-evident audit trail (SC-11.8).

Every ``audit_event`` row, whoever writes it (API, CRM, admin, sign-in), gets an HMAC seal in
``audit_seal`` in the same transaction (a mapper hook, so no writer can forget it). The check recomputes
each seal: an edited row, a deleted row (a gap in the ids) or a row inserted by hand (no seal) is reported.

The key is ``PCE_AUDIT_KEY``, else ``PCE_SECRET_KEY``. Without a stable key the seals of an earlier run cannot
be checked; the check says so instead of crying tampering. Rows written before sealing started are counted
as unsealed history, not as tampering. Rows carry ids, actions and counts, never document text.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from . import permissions
from .db import AuditEvent, AuditSeal

_KEY = (os.environ.get("PCE_AUDIT_KEY") or os.environ.get("PCE_SECRET_KEY") or "").encode()
STABLE_KEY = bool(_KEY)
if not _KEY:
    _KEY = secrets.token_bytes(32)
KEY_ID = hmac.new(_KEY, b"audit-key-id", hashlib.sha256).hexdigest()[:16]


def _mac(ev: AuditEvent) -> str:
    body = json.dumps(
        [ev.id, ev.tenant_id, ev.prospect_id, ev.at, ev.user, ev.action, ev.detail or {}],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hmac.new(_KEY, body, hashlib.sha256).hexdigest()


@event.listens_for(AuditEvent, "after_insert")
def _seal(_mapper, connection, target: AuditEvent) -> None:
    seal = AuditSeal.__table__.insert().values(event_id=target.id, key_id=KEY_ID, mac=_mac(target))
    connection.execute(seal)


def record(
    db: Session, tenant: str, user: str, action: str, prospect_id: int | None = None, **detail: Any
) -> None:
    """Add one event to the caller's transaction (sealed when it is flushed)."""
    db.add(AuditEvent(tenant_id=tenant, prospect_id=prospect_id, user=user, action=action, detail=detail))


def log(tenant: str, user: str, action: str, **detail: Any) -> None:
    """Record an event in its own transaction (sign-in events happen outside any request session)."""
    from .auth import db

    with db()() as s:
        record(s, tenant, user, action, **detail)
        s.commit()


def verify(db: Session, tenant: str) -> dict:
    """Recompute every seal. Ids are global, so a deleted row shows as a gap whichever firm it belonged to;
    only the count of gaps is shown, never another firm's rows."""
    seals = {s.event_id: s for s in db.scalars(select(AuditSeal))}
    events = {e.id: e for e in db.scalars(select(AuditEvent))}
    # Gaps the application made itself: entries removed by an erasure, listed in its own sealed entry.
    erased = {
        i
        for e in events.values()
        if e.action == "prospect.erased" and e.id in seals
        for i in (e.detail or {}).get("log_entries", [])
    }
    base = {"stable_key": STABLE_KEY, "unsealed_history": 0, "other_key": 0, "deleted": 0, "problems": []}
    if not seals:
        mine = sum(1 for e in events.values() if e.tenant_id == tenant)
        return {**base, "ok": True, "checked": 0, "unsealed_history": mine}
    first = min(seals)
    problems: list[dict] = []
    checked = other_key = deleted = 0
    for i in range(first, max(max(seals), max(events, default=first)) + 1):
        ev, seal = events.get(i), seals.get(i)
        if ev is None:
            if i not in erased:
                deleted += 1  # a seal with no row, or an id never sealed: both mean a missing row
            continue
        if ev.tenant_id != tenant:
            continue
        if seal is None:
            problems.append({"event_id": i, "problem": "not written by the application"})
        elif seal.key_id != KEY_ID:
            other_key += 1
        elif not hmac.compare_digest(seal.mac, _mac(ev)):
            problems.append({"event_id": i, "problem": "changed after it was written"})
        else:
            checked += 1
    return {
        **base,
        "ok": not problems and not deleted,
        "checked": checked,
        "unsealed_history": sum(1 for i, e in events.items() if i < first and e.tenant_id == tenant),
        "other_key": other_key,
        "deleted": deleted,
        "problems": problems[:50],
    }


# ------------------------------------------------------------------ API
router = APIRouter(prefix="/api/audit", tags=["audit"])


def _reader(request: Request) -> tuple[str, str]:
    acc = getattr(request.state, "account", None)
    role = permissions.active_role(acc.roles, request.headers.get("x-role")) if acc else None
    if acc is None or role is None or not permissions.can(role, "audit.read"):
        raise HTTPException(403, "only an admin, a viewer or a senior can read the activity log")
    return acc.tenant, acc.username


@router.get("")
def activity(
    request: Request,
    user: str | None = None,
    action: str | None = Query(None, max_length=60),
    before: int | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """The firm's activity log, newest first, with the tamper check. Reading it is itself logged."""
    from .auth import db

    tenant, me = _reader(request)
    with db()() as s:
        q = select(AuditEvent).where(AuditEvent.tenant_id == tenant)
        if user:
            q = q.where(AuditEvent.user == user)
        if action:
            q = q.where(AuditEvent.action.startswith(action, autoescape=True))
        if before:
            q = q.where(AuditEvent.id < before)
        rows = s.scalars(q.order_by(AuditEvent.id.desc()).limit(limit)).all()
        out = {
            "events": [
                {
                    "id": e.id,
                    "at": e.at,
                    "user": e.user,
                    "action": e.action,
                    "prospect_id": e.prospect_id,
                    "detail": e.detail,
                }
                for e in rows
            ],
            "check": verify(s, tenant),
        }
        record(s, tenant, me, "audit.viewed", filter_user=user, filter_action=action)
        s.commit()
    return out
