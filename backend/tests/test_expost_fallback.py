"""SC-7.9: the bank's ex-post product-cost figure fills in for missing KIDs, counted once.

Before, a client whose bank cost report stated "product costs CHF 1,500" but who uploaded no KIDs saw every
fund's ongoing charge as unknown and the bank figure only as a cross-check. KID figures (tier T3) stay
counted; the part of the bank figure (tier T4) they do not explain is added once, as a residual, and the
comparison scenarios keep per-holding product costs.
"""

from __future__ import annotations

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.finance.isin import make_synthetic_isin

A = make_synthetic_isin("EXPOSTA001")
B = make_synthetic_isin("EXPOSTB001")
BASE = {"currency": "CHF", "fee_code": None, "measurement": None, "extra": {}, "status": "extracted"}
BANK = {"institution": "Synthetic Bank", "jurisdiction": "CH", "currency": "CHF"}


def _case(
    kid_for_a: bool, report: str | None = "1500.00", period: tuple[str, str] = ("2026-01-01", "2026-12-31")
):
    docs = [
        {"id": 1, "filename": "assets.pdf", "doc_type": "portfolio_statement",
         "profile": BANK | {"as_of": "2026-09-30"}},
        {"id": 2, "filename": "kid.pdf", "doc_type": "kid", "profile": {"institution": "Synthetic AM"}},
        {"id": 3, "filename": "costs.pdf", "doc_type": "cost_report",
         "profile": BANK | {"period_start": period[0], "period_end": period[1]}},
    ]  # fmt: skip
    facts = [
        {**BASE, "id": 1, "document_id": 1, "key": "position:1", "kind": "position", "field": "market_value",
         "label": "Synthetic Equity Fund", "value": "100000.00", "isin": A},
        {**BASE, "id": 2, "document_id": 1, "key": "position:2", "kind": "position", "field": "market_value",
         "label": "Synthetic Bond Fund", "value": "100000.00", "isin": B},
    ]  # fmt: skip
    if kid_for_a:
        facts.append(
            {**BASE, "id": 3, "document_id": 2, "key": f"product:{A}:FUND_ONGOING", "kind": "product_cost",
             "field": "pct", "label": "Ongoing charges", "value": "0.80", "currency": None, "isin": A,
             "fee_code": "FUND_ONGOING", "measurement": "estimated"}
        )  # fmt: skip
    if report:
        facts.append(
            {**BASE, "id": 4, "document_id": 3, "key": "reported:product_costs", "kind": "reported",
             "field": "reported_product_costs", "label": "Product costs", "value": report,
             "measurement": "estimated"}
        )  # fmt: skip
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def _product_total(r: dict) -> str | None:
    return r["current"]["by_layer"].get("L4")


def _parent(r: dict) -> dict | None:
    return next((a for a in r["current"]["atoms"] if a["id"].endswith(":PRODUCT_REPORTED")), None)


def test_without_kids_the_bank_figure_gives_the_product_cost() -> None:
    before = _case(kid_for_a=False, report=None)
    r = _case(kid_for_a=False)
    parent = _parent(r)
    assert parent and parent["role"] == "counted" and parent["amount"] == "1500.00"
    assert parent["measurement"] == "estimated"
    assert before["current"]["is_complete"] is False
    assert not any(
        a["materiality"] == "material" and a["layer"] == "product"
        for a in r["current"]["atoms"] if a["role"] == "unknown"
    )  # fmt: skip
    assert _product_total(r) == "1500.00"


def test_with_one_kid_only_the_unexplained_part_is_added() -> None:
    r = _case(kid_for_a=True)
    kid = next(
        a for a in r["current"]["atoms"] if a["instrument_id"] == A and a["fee_code"] == "FUND_ONGOING"
    )
    assert kid["role"] == "counted" and kid["amount"] == "800.00"
    assert _parent(r)["amount"] == "700.00"
    assert _product_total(r) == "1500.00"  # not 2,300
    [recon] = [c for c in r["checks"] if c["key"].startswith("product_recon:")]
    assert "800.00" in recon["detail"] and "1,500.00" in recon["detail"]


def test_bank_figure_below_the_kids_adds_nothing_and_gaps_stay_unknown() -> None:
    r = _case(kid_for_a=True, report="600.00")
    assert _parent(r) is None
    assert _product_total(r) == "800.00"
    assert r["current"]["is_complete"] is False


def test_without_a_bank_figure_nothing_is_added() -> None:
    assert _parent(_case(kid_for_a=True, report=None)) is None


def test_part_year_report_is_annualised() -> None:
    r = _case(kid_for_a=False, report="750.00", period=("2026-01-01", "2026-06-30"))
    assert _parent(r)["amount"] == "1512.43"  # 750 x 365/181


def test_comparison_keeps_per_holding_product_costs() -> None:
    plain = _case(kid_for_a=True, report=None)
    r = _case(kid_for_a=True)
    assert r["scenarios"] == plain["scenarios"]
