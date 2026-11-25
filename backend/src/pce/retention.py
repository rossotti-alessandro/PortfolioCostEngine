"""Retention: erase prospects with no activity for ``PCE_RETENTION_DAYS`` days (SC-11.6, ADR 0004).

Run daily (docs/app/PILOT_INSTALL.md). Activity is the latest audit entry for the prospect, or its
creation date. A prospect whose CRM contact reached "won" is a client now and is kept: client records follow
the mandate's own retention rules, decided by Safe Capital, not this job.

    python -m pce.retention --days 90 [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .crm.models import Contact
from .db import AuditEvent, Prospect, make_session_factory
from .erasure import erase_prospect


def expired(db: Session, days: int, now: datetime | None = None) -> list[Prospect]:
    """Prospects whose last activity is older than ``days``, excluding those that became clients."""
    cutoff = ((now or datetime.now(UTC)) - timedelta(days=days)).isoformat(timespec="seconds")
    last = (
        select(AuditEvent.prospect_id, func.max(AuditEvent.at).label("at"))
        .where(AuditEvent.prospect_id.is_not(None))
        .group_by(AuditEvent.prospect_id)
        .subquery()
    )
    won = select(Contact.prospect_id).where(Contact.stage == "won", Contact.prospect_id.is_not(None))
    rows = db.execute(
        select(Prospect, last.c.at)
        .outerjoin(last, last.c.prospect_id == Prospect.id)
        .where(Prospect.id.not_in(won))
    ).all()
    return [p for p, at in rows if max(p.created_at, at or "") < cutoff]


def run(db: Session, days: int, dry_run: bool) -> list[dict]:
    out = []
    for p in expired(db, days):
        counts = (
            {}
            if dry_run
            else erase_prospect(db, p.tenant_id, p.id, "system.retention", "retention_expired", True)
        )
        out.append({"tenant": p.tenant_id, "prospect_id": p.id, **counts})
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m pce.retention")
    ap.add_argument("--days", type=int, default=int(os.environ.get("PCE_RETENTION_DAYS", "90")))
    ap.add_argument("--dry-run", action="store_true", help="list what would be erased, change nothing")
    a = ap.parse_args(argv)
    if a.days < 1:
        ap.error("--days must be at least 1")
    with make_session_factory()() as db:
        for row in run(db, a.days, a.dry_run):
            print(row)  # ids and counts only: the log must not name prospects
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
