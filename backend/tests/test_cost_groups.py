"""SC-7.15: every counted cost sits in a named group, and the group rows add up to the total.

Before the fix "Fremde Spesen" (THIRD_PARTY_TRADING) had no layer, landed in ``other``, counted in the
total, and the client report printed no row for it: rows CHF 14,500 under a total of CHF 14,800.
"""

from __future__ import annotations

from decimal import Decimal

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.extraction.vocab import load_taxonomy
from pce.finance.ledger import Layer
from pce.finance.scenarios import LAYER_BY_CODE
from pce.report import IT, LAYER_NAMES

PROF = {"institution": "Synthetic Bank", "jurisdiction": "CH", "currency": "CHF",
        "period_start": "2025-01-01", "period_end": "2025-12-31", "as_of": "2025-12-31"}  # fmt: skip


def _fee(i: int, code: str, label: str, value: str) -> dict:
    return {"id": i, "document_id": 1, "key": f"fee:{code}", "kind": "fee_observed", "field": "annual_amount",
            "label": label, "value": value, "currency": "CHF", "isin": None, "fee_code": code,
            "measurement": "observed", "status": "extracted", "extra": {}}  # fmt: skip


def _analyse() -> dict:
    docs = [
        {"id": 1, "filename": "cost-SYNTHETIC.pdf", "doc_type": "cost_report", "profile": PROF},
        {"id": 2, "filename": "positions-SYNTHETIC.pdf", "doc_type": "portfolio_statement", "profile": PROF},
    ]
    facts = [
        _fee(1, "MGMT_DISCRETIONARY", "Verwaltungsgebühr", "10000"),
        _fee(2, "CUSTODY_FEE", "Depotgebühr", "2000"),
        _fee(3, "BROKERAGE", "Courtage", "1500"),
        _fee(4, "THIRD_PARTY_TRADING", "Fremde Spesen", "300"),
        _fee(5, "VAT_ON_FEES", "MWST", "1000"),
        {"id": 9, "document_id": 2, "key": "pos:1", "kind": "position", "field": "market_value",
         "label": "Synthetic Equity AG", "value": "1000000", "currency": "CHF", "isin": None,
         "fee_code": None,
         "measurement": "observed", "status": "extracted", "extra": {"asset_class": "EQUITY"}},
    ]  # fmt: skip
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def test_third_party_trading_fees_count_under_trading() -> None:
    r = _analyse()
    [atom] = [a for a in r["current"]["atoms"] if a["fee_code"] == "THIRD_PARTY_TRADING"]
    assert atom["layer"] == "L3"
    assert r["current"]["by_layer"]["L3"] == "1800.00"
    assert "other" not in r["current"]["by_layer"]


def test_group_rows_add_up_to_the_total() -> None:
    cur = _analyse()["scenarios"]["current_comparable"]
    assert set(cur["by_layer"]) <= set(LAYER_NAMES)
    assert sum(Decimal(v) for v in cur["by_layer"].values()) == Decimal(cur["total_known"])


def test_client_report_names_every_layer_in_both_languages() -> None:
    assert set(LAYER_NAMES) == {layer.value for layer in Layer}
    assert all(name in IT for name in LAYER_NAMES.values())


def test_layer_by_code_follows_the_fee_table() -> None:
    table = {r["fee_code"]: r["layer"] for r in load_taxonomy("fee_taxonomy")}
    assert table, "fee_taxonomy.csv not found"
    for code, layer in LAYER_BY_CODE.items():
        assert table[code] == layer.value, code
