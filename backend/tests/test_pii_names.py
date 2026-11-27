"""SC-11.9: names, addresses and birth dates, and ``pce.pii.redact``. Every person here is SYNTHETIC.

The filters and the checker run against a fake model so the gate needs neither the ``pii`` extra nor
weights. The real model is scored on the SYNTHETIC set by the last test, which skips when it is missing.
"""

from __future__ import annotations

import socket

import pytest

from pce import pii, pii_names
from pce.pii_names import Found

TEXT = (
    "SYNTHETIC - Banca Esempio SA, Via Bank 1, 6900 Lugano\n"
    "Titolare: Marco Bernasconi & Laura Bernasconi\n"
    "Via Nassa 12\n"
    "6900 Lugano\n"
    "IBAN CH93 0076 2011 6238 5295 7\n"
    "Data di nascita: 12.03.1975\n"
    "1234567  iShares Core MSCI World UCITS ETF  IE00B4L5Y983  12'345.60\n"
    "Custodian: Julius Bär & Co. AG   Manager: Edmond de Rothschild (Suisse) S.A.\n"
    "Commissione di gestione 0.85% p.a. al 31.12.2025\n"
    "BERNASCONI M.   2/3\n"
    "Gentile Signor Bernasconi,\n"
)


def _fake(text: str, proposals: list[tuple[str, str, float]]) -> list[tuple[str, int, int, float]]:
    out = []
    for kind, value, score in proposals:
        start = text.index(value)
        out.append((kind, start, start + len(value), score))
    return out


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, float]]:
    """What the fake model proposes; tests append to it."""
    proposals: list[tuple[str, str, float]] = []
    monkeypatch.setattr(pii_names, "_propose", lambda text: _fake(text, proposals))
    monkeypatch.setattr(pii, "names_available", lambda: True)
    return proposals


def hidden(text: str) -> set[str]:
    return {text[f.start : f.end] for f in pii_names.detect(text).spans}


def test_holder_names_repeats_and_salutation_are_hidden(model: list) -> None:
    model.append(("name", "Marco Bernasconi", 0.9))
    got = hidden(TEXT)
    assert {"Marco Bernasconi", "Laura Bernasconi", "BERNASCONI M.", "Bernasconi"} <= got


def test_postcode_line_under_a_street_is_hidden(model: list) -> None:
    model.append(("address", "Via Nassa 12", 0.8))
    assert {"Via Nassa 12", "6900 Lugano"} <= hidden(TEXT)


def test_birth_date_is_kept_but_other_dates_are_not_touched(model: list) -> None:
    model.append(("birth_date", "12.03.1975", 0.9))
    out = pii.redact(TEXT)
    assert "12.03.1975" not in out
    assert "31.12.2025" in out


def test_firms_funds_roles_and_isins_are_never_masked(model: list) -> None:
    # Proposals the real model made on public documents and on the SYNTHETIC set.
    model.extend(
        [
            ("name", "Julius Bär", 0.9),
            ("name", "Edmond de Rothschild", 0.9),
            ("name", "iShares Core MSCI World", 0.6),
            ("name", "IE00B4L5Y983", 0.6),
            ("address", "Via Bank 1", 0.7),
        ]
    )
    out = pii.redact(TEXT)
    for public in (
        "Julius Bär",
        "Edmond de Rothschild",
        "iShares Core MSCI World",
        "IE00B4L5Y983",
        "Via Bank 1",
    ):
        assert public in out, public
    assert "12'345.60" in out and "0.85%" in out


@pytest.mark.parametrize(
    "word", ["Person", "Berater", "Allianz", "versicherten Person", "Titolare del conto"]
)
def test_lone_words_and_roles_are_not_names(word: str) -> None:
    assert not pii_names._keep("name", word, f"SYNTHETIC {word} text")


def test_proposals_below_high_are_hidden_and_reported_as_uncertain(model: list) -> None:
    text = "SYNTHETIC note: call with Anna Pedrazzini about the fee schedule."
    model.append(("name", "Anna Pedrazzini", 0.35))
    res = pii_names.detect(text)
    assert [text[f.start : f.end] for f in res.uncertain] == ["Anna Pedrazzini"]
    assert "Anna Pedrazzini" not in pii.redact(text)


def test_the_checker_cannot_drop_a_rule_span(model: list) -> None:
    # The model proposes a shorter span inside the IBAN: the merged mask still covers the whole IBAN.
    model.append(("name", "CH93 0076", 0.9))
    out = pii.redact(TEXT)
    assert "6238 5295" not in out and "[IBAN_1]" in out


def test_redact_without_the_model_masks_rule_identifiers_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pii, "names_available", lambda: False)
    out = pii.redact(TEXT)
    assert "[IBAN_1]" in out and "Marco Bernasconi" in out


def test_redact_raises_when_an_identifier_survives(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pii, "names_available", lambda: False)
    monkeypatch.setattr(pii, "mask", lambda text, spans: text)  # a masking bug
    with pytest.raises(pii.LeakError):
        pii.redact(TEXT)


needs_model = pytest.mark.skipif(not pii_names.available(), reason="pii extra or weights not installed")


@needs_model
def test_real_model_runs_offline_and_scores_on_the_synthetic_set(monkeypatch: pytest.MonkeyPatch) -> None:
    from evaluation.pii_set import combined, pages, score

    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("the name model tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    res = score(combined, pages(5))
    for kind in ("name", "address", "birth_date"):
        hit, total = res["recall"][kind]
        assert hit / total >= 0.9, (kind, hit, total)
    assert res["precision"][0] / res["precision"][1] >= 0.95, res["false_positive_shapes"]


def test_found_is_hashable_and_holds_no_text() -> None:
    assert {Found("name", 0, 3)} and not hasattr(Found("name", 0, 3), "text")
