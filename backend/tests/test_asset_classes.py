"""SC-7.16: every asset class gets the right product-cost rule. All data here is SYNTHETIC.

Packaged products (fund, ETF, structured) carry an embedded cost: without a KID it is UNKNOWN, never
zero, and a KID is requested. Directly held equity, bonds, listed options and futures, physical metal
and cash have no product cost, so none is invented and no KID is asked for. Their costs are the bank's
custody and trading fees, which come from the cost report like every other bank fee.
"""

from __future__ import annotations

import pytest

from pce.analysis import analyse, infer_asset_class
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.instruments.registry import class_from_cfi, class_from_figi

ISIN = "IE00B4L5Y983"  # checksum-valid; used as a SYNTHETIC holding


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("US Treasury Note 2.375% 15.05.2029", "BOND"),
        ("Global Convertible Bond Fund I CHF", "FUND"),
        ("UK Index Tracker Fund Acc", "FUND"),
        ("Swiss Re 1% Wandelanleihe 2027", "BOND"),
        ("Invesco Physical Gold ETC", "ETF"),
        ("Gold bar 1 kg 999.9", "COMMODITY"),
        ("Lingotto oro 1 kg", "COMMODITY"),
        ("Call Option Nestle Dec 2026 strike 110", "DERIVATIVE"),
        ("SMI Future Dec 2026", "DERIVATIVE"),
        ("Future Energy Fund A", "FUND"),
        ("Mini-Future Long on DAX", "STRUCTURED"),
        ("Warrant Call on UBS", "STRUCTURED"),
        ("Barrier Reverse Convertible on SMI 2027", "STRUCTURED"),
        ("Gold Mining Equity Fund", "FUND"),
        ("Goldman Sachs Group Inc", "EQUITY"),
    ],
)
def test_name_rule(name: str, expected: str) -> None:
    assert infer_asset_class(name, None) == (expected, True)


@pytest.mark.parametrize(
    ("name", "category", "expected"),
    [
        ("Nestle SA registered", "Equities", ("EQUITY", False)),
        ("Nestle SA registered", "Azioni", ("EQUITY", False)),
        ("Confederation 1.5% 2030", "Obbligazioni", ("BOND", False)),
        ("Confederation 1.5% 2030", "Fixed income", ("BOND", False)),
        ("Some position", "Derivatives", ("DERIVATIVE", False)),
        ("Some position", "Precious metals", ("COMMODITY", False)),
        # A bank's category is the exposure: an ETF under "Equities" still has an ongoing charge.
        ("iShares Core MSCI World UCITS ETF", "Equities", ("ETF", True)),
        ("Global Bond Fund I", "Bonds", ("FUND", True)),
        ("Some position", "Other", ("EQUITY", True)),
    ],
)
def test_bank_category_column(name: str, category: str, expected: tuple[str, bool]) -> None:
    assert infer_asset_class(name, category) == expected


def test_public_register_class_is_kept() -> None:
    assert infer_asset_class("iShares Core MSCI World UCITS ETF", "EQUITY", authoritative=True) == (
        "EQUITY",
        False,
    )


@pytest.mark.parametrize(
    ("cfi", "expected"),
    [
        ("ESVUFR", "EQUITY"),
        ("CEOGMS", "ETF"),
        ("CIOGES", "FUND"),
        ("DBFTFB", "BOND"),
        ("RWSCCE", "STRUCTURED"),
        ("RFSTCE", "STRUCTURED"),
        ("OCEPSN", "DERIVATIVE"),
        ("FFICSX", "DERIVATIVE"),
        ("TCXXXX", None),
    ],
)
def test_cfi_mapping(cfi: str, expected: str | None) -> None:
    assert class_from_cfi(cfi) == expected


def test_figi_option_is_a_derivative() -> None:
    assert class_from_figi({"securityType2": "Option", "marketSector": "Equity"}) == "DERIVATIVE"


def _one_holding(name: str, category: str | None) -> dict:
    docs = [
        {"id": 1, "filename": "statement-SYNTHETIC.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": "Synthetic Bank SA", "jurisdiction": "CH", "as_of": "2026-09-30"}},
    ]  # fmt: skip
    facts = [
        {"id": 1, "document_id": 1, "key": "p1", "kind": "position", "field": "market_value", "label": name,
         "value": "100000", "currency": "CHF", "isin": ISIN, "fee_code": None, "measurement": None,
         "status": "extracted", "extra": {"asset_class": category} if category else {}},
    ]  # fmt: skip
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


@pytest.mark.parametrize(
    ("name", "category", "product_code"),
    [
        ("World Equity UCITS ETF", None, "FUND_ONGOING"),
        ("Global Equity Fund A", None, "FUND_ONGOING"),
        ("iShares Core MSCI World UCITS ETF", "Equities", "FUND_ONGOING"),
        ("Barrier Reverse Convertible on SMI", None, "SP_ENTRY_COST"),
        ("Nestle SA registered", None, None),
        ("Confederation 1.5% 2030 bond", None, None),
        ("US Treasury Note 2.375% 2029", None, None),
        ("Call Option Nestle Dec 2026", None, None),
        ("Gold bar 1 kg", None, None),
        ("Nestle SA registered", "Equities", None),
    ],
)
def test_product_cost_rule_per_asset_class(name: str, category: str | None, product_code: str | None) -> None:
    r = _one_holding(name, category)
    product = [a for a in r["current"]["atoms"] if a["instrument_id"] == ISIN and a["layer"] in ("L4", "L5")]
    kid_requests = [q for q in r["requests"] if q["key"] == f"kid:{ISIN}"]
    if product_code is None:
        assert product == [] and kid_requests == []
    else:
        [atom] = product
        assert (atom["fee_code"], atom["role"], atom["amount"]) == (product_code, "unknown", None)
        assert len(kid_requests) == 1
