"""A bare "$" takes the document's dollar, and a KID cost example keeps its own currency (SC-5.19).

All pages here are SYNTHETIC lines built in code."""

from __future__ import annotations

import pytest

from pce.extraction import parsers
from pce.extraction.layout import Cell, Line, PageInfo
from pce.extraction.models import DocType, DocumentProfile, Evidence, Fact


def _page(*rows: str) -> list[PageInfo]:
    lines = [
        Line(1, [Cell(t, (10.0, 10.0 * i, 200.0, 10.0 * i + 8))], "pdfplumber-text")
        for i, t in enumerate(rows)
    ]
    return [PageInfo(1, 595.0, 842.0, "pdfplumber-text", lines)]


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (["Account Value $25,219.13"], "USD"),  # names no dollar: USD, as before
        (["Canadian Funds", "Account Value $25,219.13"], "CAD"),
        (["Valeur en dollars canadiens", "Total $1,000.00"], "CAD"),
        (["Holdings in US$ and A$", "Total $1,000.00"], "AUD"),  # "US$" printed: the bare "$" is the other
        (["Canadian Funds", "Australian dollars", "Total $1,000.00"], None),  # two other dollars: unclear
    ],
)
def test_dollar_currency(rows: list[str], expected: str | None) -> None:
    assert parsers._dollar_currency(_page(*rows)) == expected


def _fact(snippet: str, ccy: str = "USD") -> Fact:
    return Fact(
        key="k", kind="fee_observed", field="amount", label="Fee", value="10.00", currency=ccy,
        evidence=Evidence(page=1, bbox=[0, 0, 1, 1], snippet=snippet),
    )  # fmt: skip


def test_bare_dollar_facts_follow_the_document() -> None:
    prof = DocumentProfile(doc_type=DocType.CASH_STATEMENT, type_score=1.0)
    bare, named = _fact("Fee $10.00"), _fact("Fee US$10.00")
    parsers._resolve_dollars(_page("Canadian Funds"), [bare, named], prof)
    assert (bare.currency, named.currency) == ("CAD", "USD")
    assert prof.warnings == []


def test_unclear_dollar_is_no_currency_and_needs_review() -> None:
    prof = DocumentProfile(doc_type=DocType.CASH_STATEMENT, type_score=1.0)
    f = _fact("Fee $10.00")
    parsers._resolve_dollars(_page("Canadian Funds", "Australian dollars"), [f], prof)
    assert f.currency is None
    assert f.review is not None and f.review.status == "needs_review" and "dollar_unclear" in f.review.reasons
    assert prof.warnings


@pytest.mark.parametrize(
    ("cell", "rows", "expected"),
    [
        ("7 USD", [], "USD"),  # iShares IT: "Costi totali 7 USD 72 USD"
        ("13", ["Investissement de 10 000 EUR"], "EUR"),
        ("€ 12", [], "EUR"),
        ("940", ["USD 10.000 di investimento"], "USD"),
        ("940", [], None),  # nothing printed: no currency rather than a guess
    ],
)
def test_kid_example_currency(cell: str, rows: list[str], expected: str | None) -> None:
    assert parsers._example_currency(cell, _page(*rows)[0]) == expected
