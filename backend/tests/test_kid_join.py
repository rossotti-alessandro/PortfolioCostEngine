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
