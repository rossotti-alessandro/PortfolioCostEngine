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


# SC-7.20: debits of one fee at one bank are pooled across its cash statements.
def _statements(*periods: tuple[str, str]) -> tuple:
    docs, facts = [], []
    for n, (ps, pe) in enumerate(periods, start=1):
        d, f = _cash(["500.00"], (ps, pe))
        d[0]["id"] = n
        f[0] |= {"id": n, "document_id": n}
        docs += d
        facts += f
    return docs, facts


def test_four_quarterly_statements_pool_into_the_observed_annual_fee() -> None:
    quarters = [("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-30"),
                ("2026-07-01", "2026-09-30"), ("2026-10-01", "2026-12-31")]  # fmt: skip
    r = analyse({"domicile": "CH"}, *_statements(*quarters), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["role"] == "counted"
    assert atom["amount"] == "2000.00"
    assert atom["measurement"] == "observed"


def test_two_quarters_are_annualised_over_the_days_both_cover() -> None:
    r = analyse(
        {"domicile": "CH"},
        *_statements(("2026-01-01", "2026-03-31"), ("2026-04-01", "2026-06-30")),
        PROPOSAL_DEFAULTS,
    )
    [atom] = _custody(r)
    assert atom["amount"] == "2016.57"  # 1,000 x 365/181


def test_a_statement_repeating_a_period_counts_once() -> None:
    q1 = ("2026-01-01", "2026-03-31")
    r = analyse({"domicile": "CH"}, *_statements(q1, q1), PROPOSAL_DEFAULTS)
    [atom] = _custody(r)
    assert atom["amount"] == "2027.78"  # 500 x 365/90
    assert any(c["key"] == "debit_repeat:2:CUSTODY_FEE" for c in r["checks"])
