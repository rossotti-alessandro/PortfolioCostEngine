"""SC-7.19: costs paid once are shown as their own total, outside the annual total.

A structured product's entry margin became a one-off in SC-7.17, but no view printed one_off_known, so
the cost disappeared from the client report.
"""

from __future__ import annotations

import io

import pdfplumber

from pce.analysis import analyse
from pce.api import client_safe
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.report import render_client_report

ISIN = "CH0000000001"  # SYNTHETIC
PROF = {"institution": "Synthetic Bank", "jurisdiction": "CH", "currency": "CHF", "as_of": "2025-12-31"}


def _analysis() -> dict:
    docs = [
        {"id": 2, "filename": "positions-SYNTHETIC.pdf", "doc_type": "portfolio_statement", "profile": PROF},
        {
            "id": 3,
            "filename": "termsheet-SYNTHETIC.pdf",
            "doc_type": "termsheet",
            "profile": {"as_of": "2025-06-01"},
        },
    ]
    facts = [
        {"id": 1, "document_id": 2, "key": "pos:1", "kind": "position", "field": "market_value",
         "label": "Barrier Reverse Convertible on Synthetic AG", "value": "100000", "currency": "CHF",
         "isin": ISIN, "fee_code": None, "measurement": "observed", "status": "extracted", "extra": {}},
        {"id": 9, "document_id": 3, "key": "sp:entry_cost", "kind": "product_cost", "field": "rate_pct",
         "label": "Issuer margin", "value": "2.0", "currency": "CHF", "isin": ISIN,
         "fee_code": "SP_ENTRY_COST",
         "measurement": "estimated", "status": "extracted", "extra": {}},
    ]  # fmt: skip
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def test_entry_margin_is_a_one_off_total_not_annual_cost() -> None:
    cur = _analysis()["current"]
    assert cur["one_off_known"] == "2000.00"
    assert cur["total_known"] == "0.00"


def test_client_report_prints_the_one_off_total() -> None:
    r = client_safe(_analysis())
    r["prospect"] = {"code": "P-SYN", "label": "SYNTHETIC prospect", "synthetic": True}
    r["snapshot_hash"] = "0" * 64
    pdf = render_client_report(r)
    text = "".join(page.extract_text() or "" for page in pdfplumber.open(io.BytesIO(pdf)).pages)
    assert "Paid once, not in the annual total" in text
