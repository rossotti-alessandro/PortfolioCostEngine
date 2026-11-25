"""SC-9.8: a KID for the exact ISIN a client holds proves it is a packaged product, whatever its name.

Found by the realistic benchmark: French funds named like companies ("Comgest Monde C") were read as
equities, so their uploaded KIDs were ignored and the cost was reported complete without them.
"""

from __future__ import annotations

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.finance.isin import make_synthetic_isin

ISIN = make_synthetic_isin("MONDE00001")


def _facts(with_kid: bool) -> tuple[list[dict], list[dict]]:
    docs = [
        {"id": 1, "filename": "assets.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": "Synthetic Bank", "jurisdiction": "CH", "as_of": "2026-09-30",
                     "currency": "CHF"}},
        {"id": 2, "filename": "kid.pdf", "doc_type": "kid", "profile": {"institution": "Synthetic AM"}},
    ]  # fmt: skip
    base = {"currency": "CHF", "fee_code": None, "measurement": None, "extra": {}, "status": "extracted"}
    facts = [
        {**base, "id": 1, "document_id": 1, "key": "position:1", "kind": "position", "field": "market_value",
         "label": "Comgest Monde C", "value": "150000.00", "isin": ISIN},
    ]  # fmt: skip
    if with_kid:
        facts.append(
            {
                **base,
                "id": 2,
                "document_id": 2,
                "key": f"product:{ISIN}:ongoing",
                "kind": "product_cost",
                "field": "ongoing_pct",
                "label": "Ongoing charges",
                "value": "1.75",
                "currency": None,
                "isin": ISIN,
                "fee_code": "FUND_ONGOING",
                "measurement": "estimated",
            }
        )
    return docs, facts


def test_kid_for_the_held_isin_is_joined_even_when_the_name_looks_like_a_share() -> None:
    r = analyse({"domicile": "CH"}, *_facts(with_kid=True), PROPOSAL_DEFAULTS)
    atom = next(a for a in r["current"]["atoms"] if a["instrument_id"] == ISIN and a["role"] == "counted")
    assert atom["fee_code"] == "FUND_ONGOING"
    assert atom["amount"] == "2625.00"


def test_share_without_a_kid_still_gets_no_invented_product_cost() -> None:
    r = analyse({"domicile": "CH"}, *_facts(with_kid=False), PROPOSAL_DEFAULTS)
    assert not any(
        a["instrument_id"] == ISIN and a["fee_code"] == "FUND_ONGOING" for a in r["current"]["atoms"]
    )


def _kid_pages(perf_row: list[str]):
    from pce.extraction.layout import Cell, Line, PageInfo

    rows = [
        ["SYNTHETIC KID ISIN FR0011169341"],
        ["Frais de gestion et autres frais", "2,00% par an", "194 €"],
        perf_row,
    ]
    lines = [
        Line(
            1,
            [
                Cell(t, (50.0 + 200 * i, 100.0 + 20 * n, 240.0 + 200 * i, 112.0 + 20 * n))
                for i, t in enumerate(r)
            ],
            "pdfplumber-text",
        )
        for n, r in enumerate(rows)
    ]
    return [PageInfo(1, 595.0, 842.0, "pdfplumber-text", lines)]


def test_performance_fee_share_of_outperformance_is_not_a_rate_on_assets() -> None:
    """Found end to end (SC-9.8): "15% TTC au-delà de l'indice ... 5 €" was counted as 15% of the holding.
    The 15% applies to outperformance only; the KID's own cost-impact column (5 EUR on the 10,000 example)
    is the annual estimate: 0.05%."""
    from pce.extraction.models import DocType, DocumentProfile
    from pce.extraction.parsers import parse_kid

    prof = DocumentProfile(doc_type=DocType.KID, type_score=5)
    pages = _kid_pages(
        ["Commissions liées aux résultats", "15% TTC au-delà de l'indice Euro Stoxx TR.", "5 €"]
    )
    perf = next(f for f in parse_kid(pages, prof) if f.fee_code == "FUND_PERFORMANCE")
    assert perf.value == "0.05"
    assert perf.extra["share_of_outperformance_pct"] == "15"
    plain = _kid_pages(["Commissions liées aux résultats", "0,10% de la valeur", "10 €"])
    assert next(f for f in parse_kid(plain, prof) if f.fee_code == "FUND_PERFORMANCE").value == "0.10"


# SC-9.10: a plain bond has no ongoing charge; only a bond fund (or a KID for its ISIN) has one.
BOND = make_synthetic_isin("BOND000001")


def _bond(name: str, kid: bool = False) -> dict:
    docs, _ = _facts(with_kid=False)
    base = {"currency": "CHF", "fee_code": None, "measurement": None, "extra": {}, "status": "extracted"}
    facts = [
        {**base, "id": 1, "document_id": 1, "key": "position:1", "kind": "position", "field": "market_value",
         "label": name, "value": "100000.00", "isin": BOND},
    ]  # fmt: skip
    if kid:
        facts.append(
            {**base, "id": 2, "document_id": 2, "key": f"product:{BOND}:ongoing", "kind": "product_cost",
             "field": "ongoing_pct", "label": "Ongoing charges", "value": "0.40", "currency": None,
             "isin": BOND, "fee_code": "FUND_ONGOING", "measurement": "estimated"}
        )  # fmt: skip
    r = analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)
    return {a["fee_code"]: a for a in r["current"]["atoms"] if a["instrument_id"] == BOND}


def test_plain_bond_without_a_kid_has_no_product_cost() -> None:
    assert _bond("Synthetic Confederation 1.5% 2030 Bond") == {}


def test_bond_fund_without_a_kid_still_has_an_unknown_ongoing_charge() -> None:
    atoms = _bond("Synthetic Global Bond Fund I")
    assert atoms and all(a["amount"] is None for a in atoms.values())


def test_bond_with_a_kid_counts_its_ongoing_charge() -> None:
    assert _bond("Synthetic Confederation 1.5% 2030 Bond", kid=True)["FUND_ONGOING"]["amount"] == "400.00"
