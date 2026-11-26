"""SC-7.12: accounts, instruments and dated positions are stored as rows, scoped by firm and prospect.

Before, holdings existed only inside one analysis run, rebuilt from loose facts, so costs could not attach
to real objects and nothing outside could be cached against them. SYNTHETIC data only.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from pce import book_of_record
from pce.analysis import analyse
from pce.db import Account, Instrument, Position, Prospect, make_session_factory
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.erasure import erase_prospect
from pce.finance.isin import make_synthetic_isin

FUND = make_synthetic_isin("BOOKFUND01")
BASE = {"currency": "CHF", "fee_code": None, "measurement": None, "extra": {}, "status": "extracted"}


def _result() -> dict:
    docs = [
        {"id": 1, "filename": "assets.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": "Synthetic Bank", "jurisdiction": "CH", "as_of": "2026-09-30",
                     "currency": "CHF"}},
    ]  # fmt: skip
    facts = [
        {**BASE, "id": 11, "document_id": 1, "key": "position:1", "kind": "position", "field": "market_value",
         "label": "Synthetic Equity Fund", "value": "60000.00", "isin": FUND},
        {**BASE, "id": 12, "document_id": 1, "key": "position:2", "kind": "position", "field": "market_value",
         "label": "Current account CHF", "value": "40000.00", "isin": None},
        {**BASE, "id": 13, "document_id": 1, "key": "position:3", "kind": "position", "field": "market_value",
         "label": "Synthetic US Fund USD", "value": "10000.00", "currency": "USD",
         "isin": make_synthetic_isin("BOOKUSD001")},
        {**BASE, "id": 14, "document_id": 1, "key": "total:statement", "kind": "doc_total", "field": "total",
         "label": "Total assets", "value": "110000.00"},
    ]  # fmt: skip
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def _db():
    db = make_session_factory("sqlite://")()
    for tenant in ("firm-a", "firm-b"):
        db.add(Prospect(tenant_id=tenant, code="P-1", label="SYNTHETIC"))
    db.flush()
    a, b = db.scalars(select(Prospect).order_by(Prospect.id)).all()
    return db, a.id, b.id


def _rows(db, tenant: str, pid: int) -> list[tuple]:
    return [
        (p.isin, p.name, p.asset_class, p.as_of, p.currency, p.value_ccy, p.value_base, p.fact_id)
        for p in book_of_record.positions(db, tenant, pid)
    ]


def test_positions_add_up_to_the_statement_total() -> None:
    db, pa, _ = _db()
    book_of_record.sync(db, "firm-a", pa, _result())
    rows = book_of_record.positions(db, "firm-a", pa)
    assert sum(Decimal(p.value_ccy) for p in rows) == Decimal("110000.00")
    [acc] = db.scalars(select(Account)).all()
    assert (acc.institution, acc.jurisdiction) == ("Synthetic Bank", "CH")
    assert {p.as_of for p in rows} == {"2026-09-30"}
    usd = next(p for p in rows if p.currency == "USD")
    assert usd.value_base is None  # no printed USD rate: never an invented CHF value
    cash = next(p for p in rows if p.isin is None)
    assert cash.asset_class == "CASH"


def test_reimport_gives_the_same_rows() -> None:
    db, pa, _ = _db()
    book_of_record.sync(db, "firm-a", pa, _result())
    first = _rows(db, "firm-a", pa)
    book_of_record.sync(db, "firm-a", pa, _result())
    assert _rows(db, "firm-a", pa) == first
    assert len(db.scalars(select(Account)).all()) == 1
    assert len(db.scalars(select(Instrument)).all()) == 2


def test_one_firm_cannot_read_or_overwrite_another_firms_positions() -> None:
    db, pa, pb = _db()
    book_of_record.sync(db, "firm-a", pa, _result())
    book_of_record.sync(db, "firm-b", pb, _result())  # same documents, other firm
    assert book_of_record.positions(db, "firm-b", pa) == []
    assert book_of_record.positions(db, "firm-a", pb) == []
    book_of_record.sync(db, "firm-a", pa, _result())
    assert len(_rows(db, "firm-b", pb)) == 3
    # the shared instrument master holds public reference data only, never a value or an account
    assert not {"value_ccy", "value_base", "account_id", "tenant_id"} & set(
        Instrument.__table__.columns.keys()
    )


def test_erasing_a_prospect_deletes_its_book_of_record() -> None:
    db, pa, pb = _db()
    book_of_record.sync(db, "firm-a", pa, _result())
    book_of_record.sync(db, "firm-b", pb, _result())
    db.commit()
    erase_prospect(db, "firm-a", pa, "u", "prospect_request", erase_contact=False)
    assert db.scalars(select(Position).where(Position.prospect_id == pa)).all() == []
    assert db.scalars(select(Account).where(Account.prospect_id == pa)).all() == []
    assert len(book_of_record.positions(db, "firm-b", pb)) == 3
