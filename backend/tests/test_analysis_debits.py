"""SC-7.7: repeated fee debits on one cash statement are summed before they are annualised.

Before the fix every debit of the same fee shared one atom id, so the first counted and the rest only
"corroborated" it: four quarterly custody debits of CHF 500 gave CHF 500 observed instead of CHF 2,000.
"""

from __future__ import annotations

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS

BANK = "Synthetic Bank"


def _cash(debits: list[str], period: tuple[str, str] | None, per_year: int | None = None) -> tuple:
    prof = {"institution": BANK, "jurisdiction": "CH", "currency": "CHF"}
    if period:
        prof |= {"period_start": period[0], "period_end": period[1]}
    docs = [{"id": 1, "filename": "cash.pdf", "doc_type": "cash_statement", "profile": prof}]
    facts = [
        {"id": i + 1, "document_id": 1, "key": f"debit:2026-0{i + 1}-30:CUSTODY_FEE", "kind": "cash_debit",
         "field": "debit_amount", "label": "Custody fee", "value": v, "currency": "CHF", "isin": None,
         "fee_code": "CUSTODY_FEE", "measurement": "observed", "status": "extracted",
         "extra": {"booking_date": f"2026-0{i + 1}-30", "periods_per_year": per_year}}
        for i, v in enumerate(debits)
    ]  # fmt: skip
    return docs, facts


def _custody(r: dict) -> list[dict]:
    return [a for a in r["current"]["atoms"] if a["fee_code"] == "CUSTODY_FEE"]


def test_four_debits_in_a_twelve_month_statement_give_the_annual_fee() -> None:
    r = analyse({"domicile": "CH"}, *_cash(["500.00"] * 4, ("2026-01-01", "2026-12-31")), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["role"] == "counted"
    assert atom["amount"] == "2000.00"
    assert atom["measurement"] == "observed"


def test_debits_over_part_of_a_year_are_annualised_by_days_covered() -> None:
    r = analyse({"domicile": "CH"}, *_cash(["500.00"] * 2, ("2026-01-01", "2026-06-30")), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["amount"] == "2016.57"  # 1,000 x 365/181
    assert atom["measurement"] == "estimated"


def test_quarterly_debit_uses_the_stated_frequency() -> None:
    r = analyse({"domicile": "CH"}, *_cash(["500.00"], ("2026-07-01", "2026-09-30"), 4), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["amount"] == "2000.00"
    assert atom["measurement"] == "estimated"


def test_debit_with_unknown_period_is_a_flagged_lower_bound() -> None:
    r = analyse({"domicile": "CH"}, *_cash(["500.00"], None), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["amount"] == "500.00"
    assert atom["measurement"] == "estimated"
    assert "lower bound" in atom["note"]
    assert any(c["key"] == "debit_period:1:CUSTODY_FEE" and c["status"] == "warn" for c in r["checks"])
