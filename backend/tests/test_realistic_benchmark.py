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
