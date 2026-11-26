"""Book of record (SC-7.12): write the analysis's accounts, instruments and positions as rows.

The analysis already merges and checks statements (duplicates, lots, FX, asset classes), so the tables are
built from its result, never from raw facts a second time. The prospect's rows are replaced on every run,
which makes re-import idempotent: the same documents always give the same rows.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import Account, Instrument, Position
from .finance.isin import is_valid_isin


def sync(db: Session, tenant: str, prospect_id: int, result: dict) -> None:
    """Replace the prospect's accounts and positions with those in ``result``. Does not commit."""
    db.execute(delete(Position).where(Position.tenant_id == tenant, Position.prospect_id == prospect_id))
    db.execute(delete(Account).where(Account.tenant_id == tenant, Account.prospect_id == prospect_id))
    accounts: dict[str, Account] = {}
    as_of: dict[str, str | None] = {}
    for inst in result["institutions"]:
        accounts[inst["name"]] = Account(
            tenant_id=tenant,
            prospect_id=prospect_id,
            institution=inst["name"],
            jurisdiction=inst.get("jurisdiction"),
        )
        as_of[inst["name"]] = inst.get("as_of")
    db.add_all(accounts.values())
    db.flush()
    for h in result["holdings"]:
        isin = h["isin"] if h.get("isin") and is_valid_isin(h["isin"]) else None
        if isin and db.get(Instrument, isin) is None:
            # First sight wins: a later statement naming the fund differently does not rewrite the master.
            db.add(
                Instrument(isin=isin, name=h["name"], asset_class=h["asset_class"], currency=h["currency"])
            )
            db.flush()
        db.add(
            Position(
                tenant_id=tenant,
                prospect_id=prospect_id,
                account_id=accounts[h["institution"]].id,
                isin=isin,
                name=h["name"],
                asset_class=h["asset_class"],
                as_of=as_of.get(h["institution"]),
                currency=h["currency"],
                value_ccy=str(h["value_ccy"]),
                value_base=h["value"],
                fact_id=h["fact_id"],
            )
        )
    db.flush()


def positions(db: Session, tenant: str, prospect_id: int) -> list[Position]:
    """The prospect's positions, scoped by tenant: another firm's rows are never returned."""
    return list(
        db.scalars(
            select(Position)
            .where(Position.tenant_id == tenant, Position.prospect_id == prospect_id)
            .order_by(Position.id)
        )
    )
