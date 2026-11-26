"""SC-7.16: merging documents is idempotent. All data here is SYNTHETIC.

A second copy of a document (a re-download or re-export, so other bytes and no sha256 match), one ISIN
held in two lots, or the same input in another order must give the same costs as the clean input.
Before the fix a second statement, KID or termsheet raised InclusionGraphError: duplicate atom id.
"""

from __future__ import annotations

import json
import random

import pytest

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS

BANK = "Synthetic Bank SA"
FUND, SP = "IE00B4L5Y983", "CH0012345678"  # checksum-valid ISINs used as SYNTHETIC holdings


def _pack() -> tuple[list[dict], list[dict]]:
    docs = [
        {"id": 1, "filename": "statement-SYNTHETIC.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": BANK, "jurisdiction": "CH", "as_of": "2026-09-30", "currency": "CHF"}},
        {"id": 2, "filename": "costs-SYNTHETIC.pdf", "doc_type": "cost_report",
         "profile": {"institution": BANK, "jurisdiction": "CH", "period_start": "2025-10-01",
                     "period_end": "2026-09-30"}},
        {"id": 3, "filename": "kid-SYNTHETIC.pdf", "doc_type": "kid", "profile": {"as_of": "2026-03-01"}},
        {"id": 4, "filename": "termsheet-SYNTHETIC.pdf", "doc_type": "termsheet", "profile": {}},
    ]  # fmt: skip
    pos = {"kind": "position", "field": "market_value", "currency": "CHF", "fee_code": None,
           "measurement": None, "status": "extracted"}  # fmt: skip
    facts = [
        pos | {"id": 1, "document_id": 1, "key": "p1", "label": "World Equity UCITS ETF", "value": "600000",
               "isin": FUND, "extra": {}},
        pos | {"id": 2, "document_id": 1, "key": "p2", "label": "Barrier Reverse Convertible on SMI",
               "value": "200000", "isin": SP, "extra": {}},
        pos | {"id": 3, "document_id": 1, "key": "p3", "label": "Nestle SA registered", "value": "150000",
               "isin": "CH0038863350", "extra": {}},
        pos | {"id": 4, "document_id": 1, "key": "p4", "label": "Current account CHF", "value": "50000",
               "isin": None, "extra": {"asset_class": "CASH"}},
        {"id": 5, "document_id": 1, "key": "total", "kind": "doc_total", "field": "total_assets",
         "label": "Total", "value": "1000000", "currency": "CHF", "isin": None, "fee_code": None,
         "measurement": None, "status": "extracted", "extra": {}},
        {"id": 6, "document_id": 2, "key": "fee:CUSTODY_FEE", "kind": "fee_observed",
         "field": "annual_amount", "label": "Custody fee", "value": "2500.00", "currency": "CHF",
         "isin": None, "fee_code": "CUSTODY_FEE", "measurement": "observed", "status": "extracted",
         "extra": {}},
        {"id": 7, "document_id": 3, "key": "kid:ongoing", "kind": "product_cost", "field": "rate_pct",
         "label": "Ongoing costs", "value": "0.20", "currency": None, "isin": FUND,
         "fee_code": "FUND_ONGOING", "measurement": "estimated", "status": "extracted", "extra": {}},
        {"id": 8, "document_id": 4, "key": "sp:ongoing", "kind": "product_cost", "field": "rate_pct",
         "label": "Running fee", "value": "0.50", "currency": None, "isin": SP,
         "fee_code": "SP_ONGOING", "measurement": "estimated", "status": "extracted", "extra": {}},
    ]  # fmt: skip
    return docs, facts


def _run(docs: list[dict], facts: list[dict]) -> dict:
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def _copy(docs: list[dict], facts: list[dict], doc_id: int, **profile: str) -> tuple[list[dict], list[dict]]:
    """Append a second copy of one document: new ids, same content (optionally another profile)."""
    src = next(d for d in docs if d["id"] == doc_id)
    prof = src["profile"] | profile
    copy = src | {"id": 100 + doc_id, "filename": "copy-" + src["filename"], "profile": prof}
    extra = [
        f | {"id": 1000 + f["id"], "document_id": copy["id"]} for f in facts if f["document_id"] == doc_id
    ]
    return [*docs, copy], facts + extra


def _costs(r: dict) -> tuple:
    cur = r["current"]
    atoms = cur["atoms"]
    counted = sorted(
        (a["fee_code"], a["instrument_id"], a["amount"]) for a in atoms if a["role"] == "counted"
    )
    unknown = sorted((a["fee_code"], a["instrument_id"]) for a in cur["atoms"] if a["role"] == "unknown")
    return cur["total_known"], r["aum"]["total"], counted, unknown


def test_clean_pack_counts_each_product_once() -> None:
    total, aum, counted, _ = _costs(_run(*_pack()))
    assert aum == "1000000"
    assert ("FUND_ONGOING", FUND, "1200.00") in counted
    assert total == "4700.00"  # custody 2'500 + ETF 600'000 x 0.20% + SP 200'000 x 0.50%


@pytest.mark.parametrize("doc_id", [1, 3, 4], ids=["statement", "kid", "termsheet"])
def test_second_copy_of_a_document_changes_nothing(doc_id: int) -> None:
    base = _run(*_pack())
    again = _run(*_copy(*_pack(), doc_id))
    assert _costs(again) == _costs(base)
    assert any(c["key"].startswith("duplicate:") for c in again["checks"])


def test_newest_kid_wins_and_a_different_figure_is_flagged() -> None:
    docs, facts = _copy(*_pack(), 3, as_of="2026-08-01")
    facts = [f | {"value": "0.25"} if f["id"] == 1007 else f for f in facts]
    r = _run(docs, facts)
    [atom] = [a for a in r["current"]["atoms"] if a["fee_code"] == "FUND_ONGOING"]
    assert atom["amount"] == "1500.00"  # 600'000 x 0.25%, from the newer KID
    assert atom["evidence_fact_ids"] == [1007]
    assert any(c["key"] == f"duplicate:product:{FUND}" and c["status"] == "warn" for c in r["checks"])


def test_one_isin_in_two_lots_is_one_position_on_the_summed_value() -> None:
    docs, facts = _pack()
    lot = next(f for f in facts if f["id"] == 1)
    facts = [f | {"value": "400000"} if f["id"] == 1 else f for f in facts]
    facts.append(lot | {"id": 9, "key": "p1b", "value": "200000"})
    r = _run(docs, facts)
    product = [a for a in r["current"]["atoms"] if a["fee_code"] == "FUND_ONGOING"]
    assert [a["amount"] for a in product] == ["1200.00"]
    assert _costs(r) == _costs(_run(*_pack()))


def test_one_isin_in_two_lots_without_kid_is_one_unknown() -> None:
    docs, facts = _pack()
    docs = [d for d in docs if d["id"] != 3]
    lot = next(f for f in facts if f["id"] == 1)
    facts = [f for f in facts if f["document_id"] != 3] + [lot | {"id": 9, "key": "p1b"}]
    r = _run(docs, facts)
    unknown = [a for a in r["current"]["atoms"] if a["role"] == "unknown" and a["instrument_id"] == FUND]
    assert len(unknown) == 1
    [req] = [q for q in r["requests"] if q["key"] == f"kid:{FUND}"]
    assert req["assets_affected"] == "1200000"


def test_two_accounts_at_one_bank_are_both_counted() -> None:
    """A second statement with other positions is not a duplicate, even on the same date."""
    docs, facts = _copy(*_pack(), 1)
    facts = [f | {"value": "300000"} if f["id"] == 1001 else f for f in facts]
    facts = [f | {"value": "700000"} if f["id"] == 1005 else f for f in facts]
    r = _run(docs, facts)
    assert r["aum"]["total"] == "1700000"
    assert not any(c["key"].startswith("duplicate:statement") for c in r["checks"])


def test_shuffled_input_and_rerun_give_identical_output() -> None:
    docs, facts = _copy(*_pack(), 3)
    base = json.dumps(_run(docs, facts), sort_keys=True, default=str)
    assert json.dumps(_run(docs, facts), sort_keys=True, default=str) == base
    for seed in range(5):
        rnd = random.Random(seed)  # noqa: S311 - a test shuffle, not security
        d2, f2 = docs[:], facts[:]
        rnd.shuffle(d2)
        rnd.shuffle(f2)
        assert json.dumps(_run(d2, f2), sort_keys=True, default=str) == base
