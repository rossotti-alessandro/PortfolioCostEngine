"""SC-7.8: costs the holdings imply are listed even when no document quantifies them.

Before, each bank was expected to show only a service fee, custody and brokerage. A fund whose KID gave
no transaction costs, or a USD holding paying an FX margin, left no trace, so the cost picture could read
complete. Product gaps now become unknown atoms; implicit costs go to a separate list that never enters
the totals (Ale, 2026-11-25).
"""

from __future__ import annotations

from decimal import Decimal

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.finance.checklist import hidden_costs
from pce.finance.isin import make_synthetic_isin

ISIN = make_synthetic_isin("CHECK00001")
BASE = {"currency": "CHF", "fee_code": None, "measurement": None, "extra": {}, "status": "extracted"}


def _fund(kid_rows: dict[str, str], ccy: str = "CHF") -> tuple[list[dict], list[dict]]:
    docs = [
        {"id": 1, "filename": "assets.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": "Synthetic Bank", "jurisdiction": "CH", "as_of": "2026-09-30",
                     "currency": "CHF"}},
        {"id": 2, "filename": "kid.pdf", "doc_type": "kid", "profile": {"institution": "Synthetic AM"}},
    ]  # fmt: skip
    facts = [
        {**BASE, "id": 1, "document_id": 1, "key": "position:1", "kind": "position", "field": "market_value",
         "label": "Synthetic Equity Fund", "value": "100000.00", "currency": ccy, "isin": ISIN},
        {**BASE, "id": 2, "document_id": 1, "key": "fx:USD", "kind": "fx", "field": "fx_rate",
         "label": "USD/CHF", "value": "0.90", "currency": None},
    ]  # fmt: skip
    for i, (code, pct) in enumerate(kid_rows.items()):
        facts.append(
            {**BASE, "id": 10 + i, "document_id": 2, "key": f"product:{ISIN}:{code}", "kind": "product_cost",
             "field": "pct", "label": code, "value": pct, "currency": None, "isin": ISIN, "fee_code": code,
             "measurement": "estimated"}
        )  # fmt: skip
    return docs, facts


def _atoms(r: dict, code: str) -> list[dict]:
    return [a for a in r["current"]["atoms"] if a["instrument_id"] == ISIN and a["fee_code"] == code]


def test_kid_without_transaction_costs_leaves_them_unknown_not_zero() -> None:
    r = analyse({"domicile": "CH"}, *_fund({"FUND_ONGOING": "0.80"}), PROPOSAL_DEFAULTS)
    [tx] = _atoms(r, "FUND_TRANSACTION")
    assert tx["measurement"] == "unknown" and tx["amount"] is None
    assert r["current"]["is_complete"] is False
    assert r["current"]["total_known"] == "800.00"  # the unknown adds nothing to the total


def test_kid_with_transaction_costs_counts_them_once() -> None:
    r = analyse(
        {"domicile": "CH"}, *_fund({"FUND_ONGOING": "0.80", "FUND_TRANSACTION": "0.10"}), PROPOSAL_DEFAULTS
    )
    [tx] = _atoms(r, "FUND_TRANSACTION")
    assert tx["measurement"] == "estimated" and tx["amount"] == "100.00"


def test_foreign_holding_lists_an_fx_margin_outside_the_totals() -> None:
    chf = analyse({"domicile": "CH"}, *_fund({"FUND_ONGOING": "0.80"}), PROPOSAL_DEFAULTS)
    usd = analyse({"domicile": "CH"}, *_fund({"FUND_ONGOING": "0.80"}, "USD"), PROPOSAL_DEFAULTS)
    assert not any(h["fee_code"] == "FX_MARGIN" for h in chf["hidden_costs"])
    [fx] = [h for h in usd["hidden_costs"] if h["fee_code"] == "FX_MARGIN"]
    assert fx["status"] == "not_estimated" and fx["basis"] == "90000.00"
    assert not any(a["fee_code"] == "FX_MARGIN" for a in usd["current"]["atoms"])
    assert any(c["key"] == "hidden_costs" for c in usd["checks"])


def test_an_evidenced_cost_is_not_listed_again_as_hidden() -> None:
    h = [{"institution": "B", "asset_class": "EQUITY", "currency": "CHF", "value": Decimal("1000")}]
    codes = {x.fee_code for x in hidden_costs(h, "CHF", {("B", "STAMP_DUTY_CH")})}
    assert codes == {"BID_ASK_SPREAD"}
    [cash] = hidden_costs([{**h[0], "asset_class": "CASH"}], "CHF", set())
    assert cash.fee_code == "CASH_DRAG" and cash.status == "not_estimated"  # SC-7.14: listed, not invented
