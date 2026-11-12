"""SC-5.8: printed-number reader, layout-aware fee finder and value verification. SYNTHETIC data only."""

from __future__ import annotations

from decimal import Decimal

import pytest
from conftest import write_text_pdf

from pce.extraction import finder, verify
from pce.extraction.layout import Cell, Line, PageInfo
from pce.extraction.numbers import find_numbers
from pce.extraction.parsers import extract


@pytest.mark.parametrize(
    ("printed", "value", "unit", "currency"),
    [
        ("1'250.50", "1250.50", "", None),
        ("1’250.50", "1250.50", "", None),
        ("1.250,50", "1250.50", "", None),
        ("1 250,50 €", "1250.50", "", "EUR"),
        ("1,250.50", "1250.50", "", None),
        ("0,85 %", "0.85", "%", None),
        ("25 bp", "25", "bp", None),
        ("(3.28)", "-3.28", "", None),
        ("3.28-", "-3.28", "", None),
        ("CHF 125.-", "125", "", "CHF"),
        ("€0", "0", "", "EUR"),
        ("Fino a 308 Euro", "308", "", "EUR"),
        ("0.125 %", "0.125", "%", None),
        ("2.467 EUR", "2467", "", "EUR"),
    ],
)
def test_printed_numbers_to_decimal(printed, value, unit, currency):
    n = find_numbers(printed)[0]
    assert (n.value, n.unit, n.currency) == (Decimal(value), unit, currency)


@pytest.mark.parametrize(
    "text", ["31.12.2025", "2026-09-30", "USD/CHF 2026-09-30", "CH0454664001", "valid from 3a"]
)
def test_dates_isins_and_glued_digits_are_not_numbers(text):
    assert find_numbers(text) == []


def test_range_dash_is_not_a_minus_sign():
    assert [n.value for n in find_numbers("0.5 – 1.0 %")] == [Decimal("0.5"), Decimal("1.0")]


def _page(
    rows: list[list[tuple[str, float]]], y0: float = 100, step: float = 12, size: float = 8
) -> PageInfo:
    """A synthetic page: each row is a list of (text, x) cells on one line."""
    lines = []
    for i, row in enumerate(rows):
        y = y0 + i * step
        cells = [Cell(t, (x, y, x + 5 * len(t), y + size)) for t, x in row if t]
        if cells:
            lines.append(Line(1, cells, "pdfplumber-text"))
    return PageInfo(1, 595, 842, "pdfplumber-text", lines)


def test_finder_links_value_to_row_label_column_header_and_section():
    page = _page(
        [
            [("Custody fees", 50)],
            [("Portfolio value", 50), ("Rate p.a.", 300), ("Minimum", 400)],
            [("Up to CHF 1 million", 50), ("0.40 %", 300), ("CHF 250", 400)],
            [("Over CHF 1 million", 50), ("0.30 %", 300), ("CHF 250", 400)],
        ]
    )
    facts = finder.find_fees([page])
    got = {(f.value, f.label) for f in facts}
    assert ("0.40", "Custody fees › Up to CHF 1 million | Rate p.a.") in got
    assert ("250", "Custody fees › Over CHF 1 million | Minimum") in got
    f = next(f for f in facts if f.value == "0.40")
    assert f.evidence.bbox and f.evidence.label_bbox and f.evidence.row_bbox
    assert f.evidence.region == "table"
    assert all(
        Decimal(f.value) not in (Decimal(1), Decimal(1000000)) for f in facts
    )  # band limits are labels


def test_finder_joins_a_wrapped_label_beside_the_value():
    page = _page(
        [
            [("Management fees and other", 50)],
            [("administrative or operating", 50), ("149 USD", 400)],
            [("costs", 50)],
        ],
        step=9,
    )
    (f,) = finder.find_fees([page])
    assert f.label == "Management fees and other administrative or operating costs"
    assert f.value == "149" and f.currency == "USD"


@pytest.mark.parametrize(
    "row",
    [
        [("Unfavourable scenario: what you might get back after costs", 50), ("USD 7,520", 400)],
        [("Example investment", 50), ("CHF 10'000", 400)],
        [("Custody fee, see page", 50), ("2026", 400)],
        [("Custody fee: on request", 50)],
        [("World Index ETF CHF ZZWLDIDX0014", 50), ("Price", 300), ("CHF 50.00", 400)],
        [("FX rate USD/CHF", 50), ("Total fees", 300), ("0.8000", 400)],
    ],
)
def test_finder_skips_scenarios_invested_amounts_years_and_missing_values(row):
    assert finder.find_fees([_page([row])]) == []


def test_verify_flags_disagreement_keeps_value_and_records_alternative():
    page = _page([[("Custody fee", 50), ("0.25 %", 300)]])
    (f,) = finder.find_fees([page])
    second = PageInfo(
        1, 595, 842, verify.SECOND_READER, [Line(1, [Cell("0.35%", tuple(f.evidence.bbox))], "x")]
    )
    verify.verify([f], [page], [second])
    assert f.value == "0.25"  # never corrected silently
    assert f.review.status == "needs_review" and "engines_disagree" in f.review.reasons
    assert f.review.alternatives


def test_verify_accepts_when_second_reader_sees_the_same_digits():
    page = _page([[("Custody fee", 50), ("0.25 %", 300)]])
    (f,) = finder.find_fees([page])
    second = PageInfo(
        1, 595, 842, verify.SECOND_READER, [Line(1, [Cell("025%", tuple(f.evidence.bbox))], "x")]
    )
    verify.verify([f], [page], [second])
    assert f.review.status == "accepted"


def test_verify_flags_zero_in_running_text_and_ambiguous_thousands():
    page = _page(
        [[("The custody fee may be 0.00 CHF in some cases", 50)], [("Account fee", 50), ("1.250", 300)]]
    )
    facts = finder.find_fees([page])
    verify.verify(facts, [page], None)
    reasons = {f.value: f.review.reasons for f in facts}
    assert "zero_in_text" in reasons["0.00"]
    assert "separator_ambiguous" in reasons["1250"]


def test_extract_adds_reviewed_fee_mentions_with_boxes(tmp_path):
    """SYNTHETIC price schedule: every finder value has page + bbox and a review stored in extra."""
    pdf = tmp_path / "synthetic_price_schedule.pdf"
    write_text_pdf(
        pdf,
        [
            (50, 780, 12, "SYNTHETIC Bank - Price schedule 2026"),
            (50, 740, 10, "Safekeeping fees"),
            (50, 720, 9, "Portfolio value"),
            (300, 720, 9, "Rate p.a."),
            (50, 708, 9, "Up to CHF 2 million"),
            (300, 708, 9, "0.35 %"),
            (50, 696, 9, "Minimum per year"),
            (300, 696, 9, "CHF 300.00"),
        ],
    )
    res, _ = extract(pdf.name, pdf.read_bytes())
    fees = [f for f in res.facts if f.extra.get("review")]
    assert {f.value for f in fees} >= {"0.35", "300.00"}
    assert all(f.evidence.page == 1 and f.evidence.bbox for f in fees)
    assert "find_and_verify" in res.profile.timings_ms
