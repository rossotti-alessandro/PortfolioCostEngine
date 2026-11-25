"""SC-9.8: the realistic benchmark's statements are SYNTHETIC, well formed and scored exactly."""

from __future__ import annotations

import json

import pytest
from stdnum import iban, isin
from stdnum.ch import ssn

from pce.evaluation.realistic.__main__ import summarise
from pce.evaluation.realistic.generate import LAYOUTS, build, fmt
from pce.evaluation.realistic.score import page_text, score_doc
from pce.evaluation.realistic.universe import universe
from pce.extraction.parsers import extract


def test_universe_holds_only_valid_isins_and_funds_carry_their_kid_ocf() -> None:
    u = universe()
    assert len(u) > 100
    assert all(isin.is_valid(i.isin) for i in u)
    assert all(i.ocf_pct is not None and i.kid_file for i in u if i.kind in ("ETF", "FUND"))


def test_number_formats() -> None:
    from decimal import Decimal

    x = Decimal("1234567.5")
    assert [fmt(x, f) for f in ("ch", "fr", "it", "us")] == [
        "1'234'567.50",
        "1 234 567.50",
        "1.234.567,50",
        "1,234,567.50",
    ]


@pytest.fixture(scope="module")
def statements(tmp_path_factory):
    out = tmp_path_factory.mktemp("realistic")
    return out, build(out, len(LAYOUTS))


def test_every_statement_says_synthetic_and_planted_identifiers_are_well_formed(statements) -> None:
    out, golds = statements
    for g in golds:
        text = " ".join(page_text(extract(g.file, (out / g.file).read_bytes())[1]).values())
        assert "SYNTHETIC TEST DOCUMENT" in text
        kinds = {p["kind"]: p["text"] for p in g.pii}
        assert iban.is_valid(kinds["iban"])
        if "ahv" in kinds:
            assert ssn.is_valid(kinds["ahv"])
        assert kinds["email"].endswith(".example")  # reserved domain: no real mailbox
    assert json.loads((out / "gold.json").read_text())[0]["positions"]


def test_digital_statement_scores_exactly_and_counts_no_damage(statements) -> None:
    out, golds = statements
    g = next(x for x in golds if x.layout == "ch_private_en")
    data = (out / g.file).read_bytes()
    r = score_doc(g.file, data, g.__dict__, page_text(extract(g.file, data)[1]))
    assert r["words"][0] == r["words"][1]
    assert r["holdings"] == [len(g.positions), len(g.positions)]
    assert r["total_ok"]
    assert r["pii"]["damage"] == 0  # masking never removes an ISIN or a fee figure
    s = summarise([{**r, "variant": "digital", "layout": g.layout}])["digital"]
    assert s["holdings"] == 100.0


@pytest.mark.parametrize("layout", [lay.key for lay in LAYOUTS])
def test_every_layout_reads_all_holdings_the_total_and_every_fee(statements, layout: str) -> None:
    """Gaps the benchmark found on 2026-11-25: ISIN printed under the name (broker), French "Valeur"
    headers, and fee words such as "Fremde Spesen", "Commission de change", "Currency conversion fee"."""
    out, golds = statements
    g = next(x for x in golds if x.layout == layout)
    data = (out / g.file).read_bytes()
    r = score_doc(g.file, data, g.__dict__, page_text(extract(g.file, data)[1]))
    assert r["holdings"][0] == r["holdings"][1]
    assert r["total_ok"]
    assert r["fee_codes"][0] == r["fee_codes"][1]
    assert r["wrong"] == 0


def test_scanned_holdings_that_do_not_add_up_to_the_printed_total_go_to_review() -> None:
    """Benchmark 2026-11-25: on fax-quality scans and dark photos OCR drops decimal points ("79'897.04" ->
    "7989704") and every such value was shown as accepted. When OCR-read holdings do not reconcile with
    the printed total, each holding must ask for a person."""
    from pce.extraction.models import DocType, DocumentProfile, Evidence, Fact
    from pce.extraction.parsers import reconcile_positions

    def pos(v: str, kind: str = "position") -> Fact:
        return Fact(
            key=f"p{v}", kind=kind, field="market_value", label="x", value=v, evidence=Evidence(page=1)
        )

    prof = DocumentProfile(doc_type=DocType.PORTFOLIO_STATEMENT, type_score=5, engines=["rapidocr"])
    bad = [pos("7989704"), pos("1000.00"), pos("80897.04", "doc_total")]
    reconcile_positions(bad, prof)
    assert all(f.review and f.review.status == "needs_review" for f in bad if f.kind == "position")
    assert "total_not_reconciled" in bad[0].review.reasons
    good = [pos("79897.04"), pos("1000.00"), pos("80897.04", "doc_total")]
    reconcile_positions(good, prof)
    assert all(f.review is None or f.review.status == "accepted" for f in good)
    digital = DocumentProfile(doc_type=DocType.PORTFOLIO_STATEMENT, type_score=5, engines=["pdfplumber-text"])
    other = [pos("7989704"), pos("80897.04", "doc_total")]
    reconcile_positions(other, digital)
    assert other[0].review is None  # born-digital values are read exactly; a gap there means a missed row
