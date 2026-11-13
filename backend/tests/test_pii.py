"""SC-11.3: local PII detector. Every identifier below is SYNTHETIC (textbook examples, no real person)."""

from __future__ import annotations

import pytest

from pce.pii import detect, mask


def kinds(text: str) -> list[tuple[str, str]]:
    return [(s.kind, text[s.start : s.end]) for s in detect(text)]


@pytest.mark.parametrize(
    "iban",
    [
        "CH9300762011623852957",
        "CH93 0076 2011 6238 5295 7",
        "DE89 3704 0044 0532 0130 00",
        "IT60X0542811101000000123456",
    ],
)
def test_valid_ibans_are_found(iban: str) -> None:
    text = f"SYNTHETIC statement. IBAN {iban} CHF"
    assert kinds(text) == [("iban", iban)]


def test_iban_with_wrong_check_digits_is_not_flagged() -> None:
    assert detect("Ref CH94 0076 2011 6238 5295 7") == []


def test_labelled_iban_is_hidden_even_when_ocr_broke_it() -> None:
    # SC-11.9 measurement: OCR swaps 0/O, 1/l, 5/S and a narrow column wraps the number. After the
    # label "IBAN" a failed check digit means a misread, not a random number, so it is still hidden.
    assert kinds("IBAN CH93 OO76 2011 6238 5295 7") == [("iban", "CH93 OO76 2011 6238 5295 7")]
    assert kinds("IBAN CH93 0076 2011\n6238 5295 7\nCHF") == [("iban", "CH93 0076 2011\n6238 5295 7")]


def test_a_row_of_years_is_not_a_card() -> None:
    # Found on a public ETF factsheet: five performance years in a row happen to pass the Luhn check.
    assert detect("Performance\n2017 2018 2019 2020 2021") == []


def test_swiss_national_phone_without_label() -> None:
    assert kinds("SYNTHETIC\n091 123 45 67\n") == [("phone", "091 123 45 67")]
    assert detect("Total 091 123 45 CHF, units 100 200 30 40") == []


def test_account_number_with_country_prefix() -> None:
    assert kinds("Kunden-Nr. CH-12345678 page 1") == [("account", "CH-12345678")]


def test_a_found_identifier_is_hidden_wherever_it_repeats() -> None:
    text = (
        "Konto-Nr. 0235-123456.01\nROSSI M.   0235-123456.01   2/3 and mario@example.com, mario@example.com"
    )
    assert [k for k, _ in kinds(text)] == ["account", "account", "email", "email"]


def test_ahv_card_email_phone() -> None:
    text = (
        "SYNTHETIC client: AHV 756.1234.5678.97, card 4111 1111 1111 1111, "
        "mail mario.rossi@example.com, tel. +41 91 123 45 67, Tel. 091 123 45 67"
    )
    assert kinds(text) == [
        ("ahv", "756.1234.5678.97"),
        ("card", "4111 1111 1111 1111"),
        ("email", "mario.rossi@example.com"),
        ("phone", "+41 91 123 45 67"),
        ("phone", "091 123 45 67"),
    ]


def test_check_digits_reject_lookalikes() -> None:
    assert detect("Ref 756.1234.5678.98 and 4111 1111 1111 1112") == []


@pytest.mark.parametrize(
    ("text", "number"),
    [
        ("Konto-Nr. 0123-456789-01", "0123-456789-01"),
        ("Kontonummer: 12.345.678", "12.345.678"),
        ("Numero rapporto 123456", "123456"),
        ("Conto: 0101-1234567", "0101-1234567"),
        ("N° de compte 98765-43", "98765-43"),
        ("Client no. 7654321", "7654321"),
        ("Portfolio number 4455667", "4455667"),
        ("Portfolio 4512-01", "4512-01"),
        ("Relazione 123.456.7", "123.456.7"),
    ],
)
def test_labelled_account_numbers(text: str, number: str) -> None:
    assert kinds(f"SYNTHETIC {text} page 3") == [("account", number)]


def test_isins_amounts_rates_and_dates_are_not_flagged() -> None:
    text = (
        "SYNTHETIC. ISIN CH0012032048 and IE00B4L5Y983, Valor 1203204. Portfolio value: 1'234'567.89 CHF. "
        "Custody fee 0.25% p.a., OCF 1.08%. Period 01.01.2025 - 31.12.2025. Total CHF 12 345.60. "
        "Account: IE00B4L5Y983. Konto 31.12.2025, Portfolio 2025-2026, Conto 12345.60"
    )
    assert detect(text) == []


def test_overlap_keeps_the_stronger_kind() -> None:
    text = "Konto: CH9300762011623852957"
    assert kinds(text) == [("iban", "CH9300762011623852957")]


def test_mask_uses_stable_tokens_and_keeps_fees() -> None:
    text = (
        "SYNTHETIC IBAN CH93 0076 2011 6238 5295 7, again CH9300762011623852957; "
        "other DE89370400440532013000. Custody fee 0.25% on CH0012032048."
    )
    assert mask(text, detect(text)) == (
        "SYNTHETIC IBAN [IBAN_1], again [IBAN_1]; other [IBAN_2]. Custody fee 0.25% on CH0012032048."
    )


def test_span_carries_no_text() -> None:
    (span,) = detect("IBAN CH9300762011623852957")
    assert "CH93" not in span.model_dump_json()
