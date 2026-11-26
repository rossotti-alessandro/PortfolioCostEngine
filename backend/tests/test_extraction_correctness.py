"""Correctness pins for misreads the corpus found, reproduced with SYNTHETIC lines.

No OCR and no network. Each case is a number the engine must not state: a footer or an
invested amount is not a cost, an FX or order commission is not custody or advisory, a
rate range is not its lower bound, and a foreign-currency book with no printed rate is
not a CHF total.
"""

from __future__ import annotations

from decimal import Decimal as Dec

from pce.analysis import analyse, infer_asset_class, listed_assets
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.extraction.layout import Cell, Line, PageInfo
from pce.extraction.models import DocType, DocumentProfile
from pce.extraction.parsers import parse_cash_statement, parse_cost_report, parse_tariff
from pce.extraction.vocab import AMOUNT
from pce.finance.isin import make_synthetic_isin


def _page(rows: list[list[str]]) -> list[PageInfo]:
    lines = []
    for i, cells in enumerate(rows):
        y = 80.0 + i * 16
        built, x = [], 40.0
        for text in cells:
            width = max(70.0, 6.5 * len(text))
            built.append(Cell(text, (x, y, x + width, y + 10)))
            x += width + 16
        lines.append(Line(1, built, "pdfplumber-text"))
    return [PageInfo(1, 595.0, 842.0, "pdfplumber-text", lines)]


def _profile(kind: DocType) -> DocumentProfile:
    return DocumentProfile(
        doc_type=kind,
        type_score=3,
        currency="CHF",
        institution="Synthetic Bank AG",
        jurisdiction="CH",
        as_of="2026-01-01",
    )


def test_ungrouped_decimal_amount_is_money():
    """OCR drops the Swiss apostrophe: ``6'400.00`` arrives as ``6400.00`` and is still the debit."""
    assert AMOUNT.match("6400.00")
    assert not AMOUNT.match("2026")  # a year is not an amount
    prof = _profile(DocType.CASH_STATEMENT)
    pages = _page(
        [
            ["01.07.2026", "Commissione di consulenza 3° trimestre 2026", "6400.00"],
            ["01.07.2026", "Commissione di custodia 3° trimestre 2026", "1'500.00"],
        ]
    )
    debits = {f.fee_code: Dec(f.value) for f in parse_cash_statement(pages, prof)}
    assert debits == {"ADVISORY_FEE": Dec("6400.00"), "CUSTODY_FEE": Dec("1500.00")}


def test_cost_report_ignores_footer_page_numbers_and_invested_amounts():
    prof = _profile(DocType.COST_REPORT)
    pages = _page(
        [
            ["Advisory fee", "6'400.00"],
            ["Custody fee", "10'000.00", "0.25%"],  # invested amount beside the rate
            ["Custody fee", "25.00", "0.15%"],  # the money figure is the cost, the % is the rate
            ["© Synthetic Bank · Custody · Page", "4"],
        ]
    )
    fees = {f.label: Dec(f.value) for f in parse_cost_report(pages, prof) if f.kind == "fee_observed"}
    assert fees == {"Advisory fee": Dec("6400.00"), "Custody fee": Dec("25.00")}


def test_fx_and_order_commission_do_not_inherit_the_section():
    prof = _profile(DocType.TARIFF)
    pages = _page(
        [
            ["Issued by Synthetic Bank AG"],
            ["CUSTODY FEES"],
            ["Safekeeping p.a.", "0.20%"],
            ["FX commission", "0.90%"],
            ["ADVISORY"],
            ["Advisory fee p.a.", "0.80%"],
            ["Order commission", "0.25%"],
            ["Courtage", "0.10% – 0.40%"],
            ["Foreign exchange spot", "up to 1.50%"],
        ]
    )
    by_label = {f.label: f for f in parse_tariff(pages, prof) if f.fee_code}
    assert by_label["Safekeeping p.a."].fee_code == "CUSTODY_FEE"
    assert by_label["FX commission"].fee_code == "FX_COMMISSION"
    assert Dec(by_label["FX commission"].value) == Dec("0.90")
    assert by_label["Advisory fee p.a."].fee_code == "ADVISORY_FEE"
    assert by_label["Order commission"].fee_code == "BROKERAGE"
    assert "Courtage" not in by_label  # a range is not its lower bound
    assert "Foreign exchange spot" not in by_label  # a ceiling is not the rate charged


def _usd_position_facts() -> tuple[list[dict], list[dict]]:
    docs = [
        {
            "id": 16,
            "filename": "sample-statement.pdf",
            "doc_type": "portfolio_statement",
            "profile": {"institution": "Fidelity", "jurisdiction": "US", "as_of": "2026-01-01"},
        }
    ]
    facts = [
        {
            "id": 1,
            "document_id": 16,
            "key": "position:name:APPLE INC",
            "kind": "position",
            "field": "market_value",
            "label": "APPLE INC",
            "value": "13132.75",
            "currency": "USD",
            "isin": None,
            "fee_code": None,
            "measurement": None,
            "extra": {},
            "status": "accepted",
        },
        {
            "id": 2,
            "document_id": 16,
            "key": "position:name:UNPRICED NOTE",
            "kind": "position",
            "field": "market_value",
            "label": "UNPRICED NOTE",
            "value": "0.00",
            "currency": "USD",
            "isin": None,
            "fee_code": None,
            "measurement": None,
            "extra": {},
            "status": "accepted",
        },
    ]
    return docs, facts


def test_no_printed_fx_rate_refuses_a_chf_total_and_does_not_show_zero_assets():
    """SAMPLE-FIDELITY shape: positions were read in USD, the document prints no USD/CHF rate.
    The positions stay on the pipeline. Their CHF value stays missing, the prospect list does not
    publish 0, and no saving is claimed."""
    docs, facts = _usd_position_facts()
    result = analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)
    assert [h["name"] for h in result["holdings"]] == ["APPLE INC"]
    assert result["holdings"][0]["value"] is None
    assert result["holdings"][0]["value_ccy"] == "13132.75"
    assert result["aum"]["valued"] is False
    assert result["aum"]["total"] == "0"
    assert result["current"]["total_known"] == "0.00"
    assert not any(h.get("value") in ("0", "0.00", "0.0") for h in result["holdings"])
    assert not any(a["amount"] in ("0", "0.00", "0.0") for a in result["current"]["atoms"])
    check = next(c for c in result["checks"] if c["key"] == "fx_missing:Fidelity:USD")
    assert check["status"] == "fail"
    assert "13132.75" in check["detail"] or "13,132.75" in check["detail"]
    assert listed_assets(result["holdings"], result["aum"]["total"]) is None
    cmp = result["scenarios"]["same_holdings"]["comparison"]
    assert cmp["saving_claimed"] is False
    assert any("No CHF total" in c for c in cmp["caveats"])
    assert any("No saving is claimed" in c for c in cmp["caveats"])
    assert not any("higher than shown" in c or "not cheaper" in c for c in cmp["caveats"])
    report = next(r for r in result["requests"] if r["key"].startswith("cost_report:"))
    assert report["assets_affected"] is None
    assert "0%" not in report["reason"]


def test_a_zero_market_value_is_not_a_chf_holding():
    docs = [
        {
            "id": 1,
            "filename": "assets.pdf",
            "doc_type": "portfolio_statement",
            "profile": {"institution": "Synthetic Bank", "jurisdiction": "CH", "as_of": "2026-09-30"},
        }
    ]
    facts = [
        {
            "id": 1,
            "document_id": 1,
            "key": "position:ZZ",
            "kind": "position",
            "field": "market_value",
            "label": "Priced Equity",
            "value": "1000.00",
            "currency": "CHF",
            "isin": None,
            "fee_code": None,
            "measurement": None,
            "extra": {},
            "status": "accepted",
        },
        {
            "id": 2,
            "document_id": 1,
            "key": "position:unpriced",
            "kind": "position",
            "field": "market_value",
            "label": "Unpriced holding",
            "value": "0.00",
            "currency": "CHF",
            "isin": None,
            "fee_code": None,
            "measurement": None,
            "extra": {},
            "status": "accepted",
        },
    ]
    result = analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)
    assert [h["name"] for h in result["holdings"]] == ["Priced Equity"]
    assert result["aum"]["total"] == "1000.00"
    assert result["aum"]["valued"] is True
    assert listed_assets(result["holdings"], result["aum"]["total"]) == "1000.00"


def test_etf_names_are_funds_and_structured_words_stay_structured():
    """Xtrackers contains 'tracker'. It is still an ETF, so the gap is an ongoing charge."""
    assert infer_asset_class("Xtrackers MSCI World", None) == ("ETF", True)
    assert infer_asset_class("iShares Core MSCI World UCITS ETF", None) == ("ETF", True)
    assert infer_asset_class("Vanguard FTSE All-World ETF USD Acc", None) == ("ETF", True)
    assert infer_asset_class("SPDR SER TR BARCLAYS CAP HIGH YIELD BD", None) == ("ETF", True)
    assert infer_asset_class("VANGUARD INTL EQUITY INDEX FDS MSCI", None) == ("FUND", True)
    assert infer_asset_class("DOUBLELINE TOTAL RETURN BOND FD CL I", None) == ("FUND", True)
    assert infer_asset_class("ESCROW GEN MOTORS CORP BOND", None) == ("BOND", True)
    assert infer_asset_class("A UCITS share class", None) == ("ETF", True)
    assert infer_asset_class("Barrier Reverse Convertible on SMI 2027", None) == ("STRUCTURED", True)
    assert infer_asset_class("Mini-Future on Nestle", None) == ("STRUCTURED", True)
    assert infer_asset_class("Tracker Certificate on Gold", None) == ("STRUCTURED", True)
    assert infer_asset_class("APPLE INC", None) == ("EQUITY", True)
    assert infer_asset_class("Current account CHF", None) == ("CASH", True)
    # A public-register class is not overwritten by the name. A bank's "Equities" category is the
    # exposure, so there the ETF name wins (SC-7.16, tests/test_asset_classes.py).
    assert infer_asset_class("Xtrackers MSCI World UCITS ETF", "EQUITY", authoritative=True) == (
        "EQUITY",
        False,
    )


def _position(fid: int, name: str, value: str, ccy: str, isin: str | None, status: str = "extracted") -> dict:
    return {
        "id": fid,
        "document_id": 1,
        "key": f"position:{fid}",
        "kind": "position",
        "field": "market_value",
        "label": name,
        "value": value,
        "currency": ccy,
        "isin": isin,
        "fee_code": None,
        "measurement": None,
        "extra": {},
        "status": status,
    }


def _statement(institution: str = "Synthetic Bank") -> dict:
    return {
        "id": 1,
        "filename": "assets.pdf",
        "doc_type": "portfolio_statement",
        "profile": {
            "institution": institution,
            "jurisdiction": "CH",
            "as_of": "2026-09-30",
            "currency": "CHF",
        },
    }


def test_missing_kid_is_an_unknown_ongoing_charge_for_an_etf_not_an_issuer_margin():
    isin = make_synthetic_isin("XTRACK0001")
    equity = make_synthetic_isin("EQUITY0001")
    structured = make_synthetic_isin("BARRIER001")
    facts = [
        _position(1, "Xtrackers MSCI World", "100000.00", "CHF", isin),
        _position(2, "APPLE INC", "50000.00", "CHF", equity),
        _position(3, "Current account CHF", "10000.00", "CHF", None),
        _position(4, "Barrier Reverse Convertible on SMI", "20000.00", "CHF", structured),
    ]
    result = analyse({"domicile": "CH"}, [_statement()], facts, PROPOSAL_DEFAULTS)
    atoms = result["current"]["atoms"]
    etf = next(a for a in atoms if a["instrument_id"] == isin)
    assert etf["fee_code"] == "FUND_ONGOING"
    assert etf["layer"] == "L4"
    assert etf["measurement"] == "unknown" and etf["amount"] is None and etf["role"] == "unknown"
    assert "ongoing charge" in etf["note"]
    # Unchecked lines are still used, and they stay unchecked.
    assert result["holdings"][0]["status"] == "extracted"
    assert not any(a["instrument_id"] == equity and a["fee_code"] == "FUND_ONGOING" for a in atoms)
    assert not any(a["fee_code"] == "FUND_ONGOING" and "account" in a["label"].lower() for a in atoms)
    barrier = next(a for a in atoms if a["instrument_id"] == structured and a["measurement"] == "unknown")
    assert barrier["fee_code"] == "SP_ENTRY_COST"
    assert barrier["layer"] == "L5"


def test_kid_with_the_same_isin_still_counts_the_ongoing_charge():
    """The join is exact-ISIN only. A different share class, or no KID, must not produce this amount."""
    isin = make_synthetic_isin("FUNDJOIN01")
    other = make_synthetic_isin("OTHER00001")
    holding = _position(1, "Global Equity Leaders Fund A CHF", "100000.00", "CHF", isin, status="accepted")
    kid = {
        "id": 2,
        "filename": "kid.pdf",
        "doc_type": "kid",
        "profile": {"institution": "Synthetic AM", "as_of": "2026-02-15"},
    }
    rate = {
        "id": 9,
        "document_id": 2,
        "key": f"product:{isin}:ongoing",
        "kind": "product_cost",
        "field": "ongoing_pct",
        "label": "Ongoing charges",
        "value": "1.08",
        "currency": None,
        "isin": isin,
        "fee_code": "FUND_ONGOING",
        "measurement": "estimated",
        "extra": {},
        "status": "extracted",
    }
    joined = analyse({"domicile": "CH"}, [_statement(), kid], [holding, rate], PROPOSAL_DEFAULTS)
    atom = next(
        a
        for a in joined["current"]["atoms"]
        if a["instrument_id"] == isin and a["fee_code"] == "FUND_ONGOING" and a["role"] == "counted"
    )
    assert atom["amount"] == "1080.00"
    assert "1080" not in (atom["formula"] or "") or "1.08" in atom["formula"]
    # A KID for another ISIN does not attach, and the gap stays unknown rather than zero.
    rate["isin"] = other
    missed = analyse({"domicile": "CH"}, [_statement(), kid], [holding, rate], PROPOSAL_DEFAULTS)
    gap = next(a for a in missed["current"]["atoms"] if a["instrument_id"] == isin)
    assert gap["measurement"] == "unknown" and gap["amount"] is None and gap["role"] == "unknown"


def test_unvalued_etf_states_an_unknown_product_cost_and_claims_no_saving():
    isin = make_synthetic_isin("USDETF0001")
    facts = [_position(1, "Xtrackers MSCI World UCITS ETF", "25000.00", "USD", isin)]
    docs = [
        {
            "id": 1,
            "filename": "fidelity.pdf",
            "doc_type": "portfolio_statement",
            "profile": {"institution": "Fidelity", "jurisdiction": "US", "as_of": "2026-01-01"},
        }
    ]
    result = analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)
    held = result["holdings"][0]
    assert held["asset_class"] == "ETF" and held["value"] is None
    gap = next(a for a in result["current"]["atoms"] if a["instrument_id"] == isin)
    assert gap["fee_code"] == "FUND_ONGOING" and gap["amount"] is None and gap["role"] == "unknown"
    assert result["scenarios"]["same_holdings"]["comparison"]["saving_claimed"] is False
    assert result["scenarios"]["optimized"]["comparison"]["saving_claimed"] is False
    assert listed_assets(result["holdings"], result["aum"]["total"]) is None
