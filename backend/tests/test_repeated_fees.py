"""SC-7.17: fee lines with one code are summed in a report; two reports from one bank never add up.

Before the fix every fee line became atom ``cur:<bank>:<code>``, so a second line with the same code
("Custody fee" and "Custody surcharge") or a second cost report from the same bank raised
InclusionGraphError and the whole analysis failed.
"""

from __future__ import annotations

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS

BANK = "Synthetic Bank"


def _report(doc_id: int, period: tuple[str, str], lines: list[tuple[str, str, str]]) -> tuple[dict, list]:
    prof = {"institution": BANK, "jurisdiction": "CH", "currency": "CHF",
            "period_start": period[0], "period_end": period[1]}  # fmt: skip
    doc = {
        "id": doc_id,
        "filename": f"cost-{doc_id}-SYNTHETIC.pdf",
        "doc_type": "cost_report",
        "profile": prof,
    }
    facts = [
        {"id": doc_id * 100 + i, "document_id": doc_id, "key": f"fee:{code}", "kind": "fee_observed",
         "field": "annual_amount", "label": label, "value": value, "currency": "CHF", "isin": None,
         "fee_code": code, "measurement": "observed", "status": "extracted", "extra": {}}
        for i, (code, label, value) in enumerate(lines)
    ]  # fmt: skip
    return doc, facts


def _run(*reports: tuple[dict, list]) -> dict:
    docs = [d for d, _f in reports]
    facts = [f for _d, fs in reports for f in fs]
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def _custody(r: dict) -> list[dict]:
    return [a for a in r["current"]["atoms"] if a["fee_code"] == "CUSTODY_FEE"]


YEAR = ("2025-01-01", "2025-12-31")


def test_two_lines_with_one_code_in_a_report_are_summed() -> None:
    r = _run(
        _report(
            1, YEAR, [("CUSTODY_FEE", "Custody fee", "2000"), ("CUSTODY_FEE", "Custody surcharge", "150")]
        )
    )
    [atom] = _custody(r)
    assert atom["role"] == "counted"
    assert atom["amount"] == "2150.00"
    assert "2 lines" in atom["formula"]


def test_a_second_report_for_the_same_period_corroborates_and_is_counted_once() -> None:
    r = _run(
        _report(1, YEAR, [("CUSTODY_FEE", "Custody fee", "2000")]),
        _report(2, YEAR, [("CUSTODY_FEE", "Custody fee", "2000")]),
    )
    roles = sorted(a["role"] for a in _custody(r))
    assert roles == ["corroborating", "counted"]
    assert r["current"]["by_layer"]["L2"] == "2000.00"


def test_a_mismatching_copy_of_the_same_period_is_flagged() -> None:
    r = _run(
        _report(1, YEAR, [("CUSTODY_FEE", "Custody fee", "2000")]),
        _report(2, YEAR, [("CUSTODY_FEE", "Custody fee", "2500")]),
    )
    assert r["current"]["by_layer"]["L2"] == "2000.00"
    assert any(c["status"] == "warn" and "does not match" in c["detail"] for c in r["checks"])


def test_with_two_years_only_the_latest_report_counts() -> None:
    r = _run(
        _report(1, ("2024-01-01", "2024-12-31"), [("CUSTODY_FEE", "Custody fee", "1800")]),
        _report(2, YEAR, [("CUSTODY_FEE", "Custody fee", "2000")]),
    )
    [atom] = _custody(r)
    assert atom["amount"] == "2000.00"
    assert any(c["key"] == "older_report:1:CUSTODY_FEE" for c in r["checks"])
