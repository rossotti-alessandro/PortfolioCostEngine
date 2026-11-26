"""SC-7.18: transaction lists become dated trade rows with evidence. All data here is SYNTHETIC.

Trading costs (brokerage, stamp duty, FX margin) scale with turnover, which no document gave the engine
before: a buy or sell line was skipped, and an FX conversion line was read as an FX *commission* of the
whole converted amount.
"""

from __future__ import annotations

from decimal import Decimal as Dec

from sqlalchemy import select

from pce import book_of_record
from pce.analysis import analyse
from pce.db import Prospect, Transaction, make_session_factory
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.erasure import erase_prospect
from pce.extraction.layout import Cell, Line, PageInfo
from pce.extraction.models import DocType, DocumentProfile
from pce.extraction.parsers import parse_cash_statement

NESTLE = "CH0038863350"
ETF = "IE00B5BMR087"
BOND = "CH1234567894"


def _page(rows: list[list[str]]) -> list[PageInfo]:
    lines = []
    for i, cells in enumerate(rows):
        y, x, built = 80.0 + i * 16, 40.0, []
        for text in cells:
            width = max(70.0, 6.5 * len(text))
            built.append(Cell(text, (x, y, x + width, y + 10)))
            x += width + 16
        lines.append(Line(1, built, "pdfplumber-text"))
    return [PageInfo(1, 595.0, 842.0, "pdfplumber-text", lines)]


PROF = DocumentProfile(
    doc_type=DocType.CASH_STATEMENT, type_score=3, currency="CHF", institution="Synthetic Bank AG",
    jurisdiction="CH", as_of="2026-03-31",
)  # fmt: skip

LIST = [
    ["Date", "Transaction", "Security", "ISIN", "Quantity", "Price", "Amount"],
    ["03.02.2026", "Buy", "Nestle SA", NESTLE, "100", "95.20", "9'520.00"],
    ["03.02.2026", "Brokerage", "Nestle SA", "45.00"],
    ["10.03.2026", "Sell", "S&P 500 UCITS ETF", ETF, "USD", "20", "500.00", "10'000.00"],
    ["11.03.2026", "Acquisto", "Obbligazione 2030", BOND, "50'000", "99.50", "49'750.00"],
    ["12.03.2026", "Buy", "Nestle SA", NESTLE, "10", "95.20", "9'999.00"],
    ["20.03.2026", "FX spot USD/CHF", "10'000.00"],
    ["25.03.2026", "Dividend", "Nestle SA", NESTLE, "300.00"],
]


def _trades() -> list:
    return [f for f in parse_cash_statement(_page(LIST), PROF) if f.kind == "transaction"]


def test_each_trade_line_is_one_transaction_with_evidence() -> None:
    got = [(f.extra["booking_date"], f.extra["side"], f.isin, f.extra["quantity"], f.value, f.currency)
           for f in _trades()]  # fmt: skip
    assert got == [
        ("2026-02-03", "buy", NESTLE, "100", "9520.00", "CHF"),
        ("2026-03-10", "sell", ETF, "20", "10000.00", "USD"),
        ("2026-03-11", "buy", BOND, "50000", "49750.00", "CHF"),  # bond: nominal × price %
        ("2026-03-12", "buy", NESTLE, None, "9999.00", "CHF"),  # 10 × 95.20 ≠ 9'999: quantity not trusted
        ("2026-03-20", "fx", None, None, "10000.00", "CHF"),
    ]
    assert all(f.evidence.page == 1 and f.evidence.bbox and f.measurement == "observed" for f in _trades())
    assert len({f.key for f in _trades()}) == 5


def test_fees_on_the_same_list_stay_fee_debits_and_fx_conversion_is_not_a_commission() -> None:
    debits = [
        (f.fee_code, f.value) for f in parse_cash_statement(_page(LIST), PROF) if f.kind == "cash_debit"
    ]
    assert debits == [("BROKERAGE", "45.00")]  # not FX_COMMISSION 10'000 for the conversion line


# ------------------------------------------------------------------ analysis + book of record


def _facts(doc_id: int, first_id: int) -> list[dict]:
    return [
        {"id": first_id + i, "document_id": doc_id, "key": f.key, "kind": f.kind, "field": f.field,
         "label": f.label, "value": f.value, "currency": f.currency, "isin": f.isin, "fee_code": f.fee_code,
         "measurement": f.measurement, "extra": f.extra, "status": "extracted"}
        for i, f in enumerate(_trades())
    ]  # fmt: skip


def _doc(i: int, period_end: str = "2026-03-31") -> dict:
    return {"id": i, "filename": f"transactions-{i}-SYNTHETIC.pdf", "doc_type": "cash_statement",
            "profile": {"institution": "Synthetic Bank AG", "jurisdiction": "CH",
                        "period_start": "2026-01-01", "period_end": period_end}}  # fmt: skip


def test_a_second_copy_of_the_list_adds_no_trade_but_two_identical_fills_in_one_list_stay() -> None:
    one = analyse({"domicile": "CH"}, [_doc(1)], _facts(1, 1), PROPOSAL_DEFAULTS)
    two = analyse({"domicile": "CH"}, [_doc(1), _doc(2)], _facts(1, 1) + _facts(2, 101), PROPOSAL_DEFAULTS)
    assert len(one["transactions"]) == 5
    assert [t["fact_id"] for t in two["transactions"]] == [t["fact_id"] for t in one["transactions"]]
    fills = _facts(1, 1)
    fills.append({**fills[0], "id": 50, "key": "trade:extra"})  # same day, same size: a second fill
    again = analyse({"domicile": "CH"}, [_doc(1)], fills, PROPOSAL_DEFAULTS)
    assert len(again["transactions"]) == 6
    # trades are not costs: the cost totals are untouched
    assert one["current"] == analyse({"domicile": "CH"}, [_doc(1)], [], PROPOSAL_DEFAULTS)["current"]


def _db():
    db = make_session_factory("sqlite://")()
    for tenant in ("firm-a", "firm-b"):
        db.add(Prospect(tenant_id=tenant, code="P-1", label="SYNTHETIC"))
    db.flush()
    a, b = db.scalars(select(Prospect).order_by(Prospect.id)).all()
    return db, a.id, b.id


def test_rows_are_stored_idempotently_scoped_by_firm_and_erased() -> None:
    db, pa, pb = _db()
    result = analyse({"domicile": "CH"}, [_doc(1)], _facts(1, 1), PROPOSAL_DEFAULTS)
    book_of_record.sync(db, "firm-a", pa, result)
    book_of_record.sync(db, "firm-a", pa, result)  # re-import
    rows = book_of_record.transactions(db, "firm-a", pa)
    assert [(t.booking_date, t.side, t.isin, t.quantity, t.gross_ccy, t.currency) for t in rows] == [
        ("2026-02-03", "buy", NESTLE, "100", "9520.00", "CHF"),
        ("2026-03-10", "sell", ETF, "20", "10000.00", "USD"),
        ("2026-03-11", "buy", BOND, "50000", "49750.00", "CHF"),
        ("2026-03-12", "buy", NESTLE, None, "9999.00", "CHF"),
        ("2026-03-20", "fx", None, None, "10000.00", "CHF"),
    ]
    assert rows[0].account_id is not None and Dec(rows[0].gross_ccy) == Dec("9520")
    assert book_of_record.transactions(db, "firm-b", pa) == []  # another firm sees nothing
    assert book_of_record.transactions(db, "firm-b", pb) == []
    erase_prospect(db, "firm-a", pa, "u", "prospect_request", erase_contact=False)
    assert db.scalars(select(Transaction)).all() == []
