"""SC-5.21: fees the finder reads are kept, and keep their full context label (SYNTHETIC data only)."""

from __future__ import annotations

import pytest
from test_extraction_strategy import _page

from pce.extraction import finder, parsers, verify
from pce.extraction.models import Evidence, Fact


@pytest.fixture(autouse=True)
def _no_second_reader(monkeypatch):
    # The cross-check logic is under test, not Tesseract: no second reading.
    monkeypatch.setattr(verify, "second_reading", lambda data, facts: None)


def _fact(kind: str, label: str, value: str, bbox: list[float], page: int = 1) -> Fact:
    return Fact(
        key=f"{kind}:{label}:{value}",
        kind=kind,
        field="amount",
        label=label,
        value=value,
        evidence=Evidence(page=page, bbox=bbox, snippet=label),
    )


def test_total_row_beside_parser_read_components_is_kept_as_a_mention():
    """SYNTHETIC KID: entry and ongoing costs read by the type parser, "Total costs" only by the finder.
    The total stays visible as a fee_mention (outside the totals, so it cannot double count)."""
    parsed = [
        _fact("product_cost", "Entry costs", "300", [400, 100, 430, 110]),
        _fact("product_cost", "Ongoing costs", "82", [400, 120, 430, 130]),
    ]
    found = [
        _fact("fee_mention", "Entry costs", "300", [400, 100, 430, 110]),
        _fact("fee_mention", "Ongoing costs", "82", [400, 120, 430, 130]),
        _fact("fee_mention", "Total costs", "382", [400, 140, 430, 150]),
    ]
    extra = parsers._cross_check(parsed, found, b"")
    assert [(f.label, f.value, f.kind) for f in extra] == [("Total costs", "382", "fee_mention")]


def test_agreeing_readers_keep_the_parser_label_and_the_finder_context():
    """SYNTHETIC tariff: the parser's short label stays (ledger, report and translations use it); the
    finder's label with section and column is kept beside it as context for the analyst."""
    parsed = [_fact("fee_rule", "Minimum", "120", [400, 100, 430, 110])]
    found = [_fact("fee_mention", "Transaction fees › Equities | Minimum", "120", [400, 100, 430, 110])]
    parsers._cross_check(parsed, found, b"")
    assert parsed[0].label == "Minimum"
    assert parsed[0].extra["finder_label"] == "Transaction fees › Equities | Minimum"


def test_fee_row_is_kept_when_a_far_column_header_looks_like_a_return():
    """SYNTHETIC two-column factsheet: "Einstiegskosten 5,26 %" sits under a risk table's "Max. Gewinn (%)"
    header. The row names a fee, so the unrelated header does not veto it."""
    page = _page(
        [
            [("Risikobetrachtung", 50), ("Max. Gewinn (%)", 250)],
            [("Fonds (3 Jahre)", 50), ("63,4", 260)],
            [("Konditionen", 50), ("Fondspreise", 300)],
            [("Einstiegskosten", 50), ("5,26 %", 260), ("52-Wochen-Hoch", 300), ("166,12", 450)],
        ]
    )
    assert ("5.26", "%") in {(f.value, f.extra["unit"]) for f in finder.find_fees([page])}


def test_scenario_row_with_cost_words_is_still_skipped():
    """SYNTHETIC KID: the label itself is a scenario, so it stays out even though it says "costs"."""
    page = _page([[("Unfavourable scenario: what you might get back after costs", 50), ("EUR 7,520", 400)]])
    assert finder.find_fees([page]) == []


def test_long_all_caps_title_names_the_fee_of_the_rows_below():
    """SYNTHETIC Italian tariff: the fee word sits only in a long upper-case title above the rows."""
    page = _page(
        [
            [
                (
                    "BUONI ORDINARI DEL TESORO - COMMISSIONE SUL CONTROVALORE DELL'OPERAZIONE",
                    130,
                )
            ],
            [("Con durata residua fino a 80 giorni", 50), ("0,100 %", 500)],
        ]
    )
    (f,) = finder.find_fees([page])
    assert f.value == "0.100" and f.label.startswith("BUONI ORDINARI")


def test_section_title_far_above_a_long_tier_table_still_names_the_fee():
    """SYNTHETIC long tariff: "Transaction fees" is printed 50 rows above the last tier row."""
    rows = [[("Transaction fees", 50)], [("Money market investments", 50)]]
    rows += [[(f"Tier {i}", 50), ("0.300 %", 300)] for i in range(50)]
    facts = finder.find_fees([_page(rows, step=10)])
    assert len(facts) == 50 and all(f.label.startswith("Transaction fees") for f in facts)


@pytest.mark.parametrize(
    "row",
    [
        [("Investment EUR 10,000", 50), ("1.91% before costs and 1.15% after costs.", 300)],
        [("coûts et de", 50), ("6.19% après déduction des coûts.", 300)],
        [("COMMISSIONE MASSIMA APPLICABILE PER OGNI 100 EURO DI CAPITALE", 50)],
    ],
)
def test_returns_and_charging_bases_are_not_fees(row):
    """SYNTHETIC: a return quoted before/after costs, and the base a commission is charged on, under a
    section title that names costs."""
    assert finder.find_fees([_page([[("Costs over time", 50)], row])]) == []


def test_margin_interest_paid_is_a_cost_and_credit_interest_is_not():
    """SYNTHETIC statement: interest charged on a margin loan is a cost; interest earned is not."""
    page = _page([[("Margin Interest", 50), ("-1,673.75", 300)], [("Credit interest", 50), ("12.50", 300)]])
    assert [f.value for f in finder.find_fees([page])] == ["-1673.75"]
