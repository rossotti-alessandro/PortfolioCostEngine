"""SYNTHETIC CRM book for the demo. Every name is an invented star/constellation name, every amount is
made up, and every row has ``synthetic=True``. Deterministic (seeded RNG), idempotent per tenant."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import Prospect
from ..demo import spec
from .models import FUNNEL_STAGES, LOST_REASONS, Activity, Contact, StageEvent

NAMES = [
    "Altair", "Vega", "Lyra", "Orion", "Sirius", "Rigel", "Deneb", "Capella", "Antares", "Polaris",
    "Mira", "Castor", "Pollux", "Electra", "Maia", "Alcor", "Mizar", "Spica", "Arcturus", "Bellatrix",
    "Hadar", "Nunki", "Shaula", "Algol", "Atria", "Avior", "Merak", "Dubhe", "Alioth", "Mintaka",
    "Alnilam", "Saiph", "Tarazed", "Sadr", "Enif", "Markab", "Hamal", "Menkar", "Naos", "Wezen",
]  # fmt: skip
KIND_SUFFIX = {
    "family": "family",
    "individual": "(private client)",
    "company": "Holding SA",
    "foundation": "Foundation",
}
OWNERS = ["analyst", "rm.lugano", "rm.zurich"]
BANKS = [
    "Bank Alpha (Synthetic) SA",
    "Bank Beta (Synthetic) AG",
    "Bank Gamma (Synthetic) SpA",
    "Broker Delta (Synthetic) LLC",
]
SOURCES = ["referral", "referral", "intermediary", "network", "event", "website"]
# Furthest stage reached: weights shape a realistic funnel (about 1 in 6 leads becomes a client).
FAR_WEIGHTS = [10, 7, 5, 5, 6, 7]
START = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
TODAY = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)


def _iso(d: datetime) -> str:
    return d.isoformat(timespec="seconds")


def seed_contacts(db: Session, c: Any, move: Callable[..., None]) -> int:
    if db.scalar(
        select(Contact.id).where(Contact.tenant_id == c.tenant, Contact.synthetic.is_(True)).limit(1)
    ):
        return 0
    rng = random.Random(1042)  # noqa: S311 - demo data, not security
    added = 0
    for i, star in enumerate(NAMES):
        kind = rng.choice(["family", "family", "individual", "company", "foundation"])
        created = START + timedelta(days=int(i * 7.2) + rng.randint(0, 4), hours=rng.randint(0, 7))
        aum = None if rng.random() < 0.12 else str(rng.choice(range(1, 40)) * 250_000)
        k = Contact(
            tenant_id=c.tenant,
            name=f"{star} {KIND_SUFFIX[kind]}",
            kind=kind,
            email=f"{star.lower()}@example.invalid",
            domicile=rng.choice(["CH", "CH", "CH", "IT", "DE"]),
            source=rng.choice(SOURCES),
            owner=rng.choice(OWNERS),
            estimated_aum=aum,
            current_banks=rng.sample(BANKS, rng.randint(1, 2)),
            stage="lead",
            synthetic=True,
            created_at=_iso(created),
            updated_at=_iso(created),
        )
        db.add(k)
        db.flush()
        db.add(
            StageEvent(
                tenant_id=c.tenant,
                contact_id=k.id,
                from_stage=None,
                to_stage="lead",
                at=k.created_at,
                user=k.owner,
                note="SYNTHETIC",
            )
        )
        far = rng.choices(range(len(FUNNEL_STAGES)), FAR_WEIGHTS)[0]
        t = created
        for s in FUNNEL_STAGES[1 : far + 1]:
            t += timedelta(days=rng.randint(4, 28), hours=rng.randint(0, 6))
            if t > TODAY:
                break
            move(db, c, k, s, at=_iso(t))
        if k.stage != "won" and (TODAY - t).days > 45 and rng.random() < 0.75:
            t += timedelta(days=rng.randint(5, 30))
            if t <= TODAY:
                move(db, c, k, "lost", note="SYNTHETIC", at=_iso(t))
                k.lost_reason = rng.choice(list(LOST_REASONS)[:-1])
        if k.stage not in ("won", "lost"):
            due = TODAY + timedelta(days=rng.randint(-3, 14))
            k.next_action = {
                "lead": "Intro call",
                "qualified": "Ask for bank statements and price lists",
                "documents_received": "Upload documents to FeeLens",
                "cost_review": "Finish cost review and approve figures",
                "proposal_sent": "Follow up on proposal",
            }[k.stage]
            k.next_action_due = due.date().isoformat()
        db.add(
            Activity(
                tenant_id=c.tenant,
                contact_id=k.id,
                kind="call",
                at=k.created_at,
                user=k.owner,
                summary="SYNTHETIC: first contact, interested in an independent cost review.",
            )
        )
        added += 1

    p = db.scalar(select(Prospect).where(Prospect.tenant_id == c.tenant, Prospect.code == spec.PROSPECT_CODE))
    k = Contact(
        tenant_id=c.tenant,
        name=spec.PROSPECT_LABEL,
        kind="family",
        domicile=spec.CLIENT_DOMICILE,
        source="referral",
        owner="analyst",
        estimated_aum="4300000",
        current_banks=[spec.ALPHA, spec.BETA],
        stage="lead",
        prospect_id=p.id if p else None,
        synthetic=True,
        created_at=_iso(TODAY - timedelta(days=40)),
        next_action="Finish cost review and approve figures",
        next_action_due=(TODAY + timedelta(days=3)).date().isoformat(),
    )
    db.add(k)
    db.flush()
    db.add(
        StageEvent(
            tenant_id=c.tenant,
            contact_id=k.id,
            from_stage=None,
            to_stage="lead",
            at=k.created_at,
            user="analyst",
            note="SYNTHETIC",
        )
    )
    for d, s in ((32, "qualified"), (20, "documents_received"), (6, "cost_review")):
        move(db, c, k, s, at=_iso(TODAY - timedelta(days=d)))
    db.commit()
    return added + 1
