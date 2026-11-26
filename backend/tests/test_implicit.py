"""SC-7.14: cash drag as a range beside the totals. All data SYNTHETIC; the SNB is a mock transport."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.finance import implicit

BANK = "Synthetic Bank SA"
RATES = {
    "USD": {"benchmark": "SOFR", "rate_pct": "3.7883", "months": ["2025-10", "2026-09", 12],
            "source": implicit.SOURCE, "url": implicit.SNB_URL},
    "CHF": {"benchmark": "SARON", "rate_pct": "-0.0603", "months": ["2025-10", "2026-09", 12],
            "source": implicit.SOURCE, "url": implicit.SNB_URL},
}  # fmt: skip


def test_range_runs_from_zero_to_benchmark_times_cash() -> None:
    assert implicit.cash_drag_range(Decimal("100000"), Decimal("3.7883")) == (Decimal(0), Decimal("3788.3"))


def test_negative_benchmark_gives_no_drag() -> None:
    assert implicit.cash_drag_range(Decimal("100000"), Decimal("-0.0603")) == (Decimal(0), Decimal(0))


def _pack() -> tuple[list[dict], list[dict]]:
    docs = [
        {"id": 1, "filename": "statement-SYNTHETIC.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": BANK, "jurisdiction": "CH", "as_of": "2026-09-30"}},
        {"id": 2, "filename": "costs-SYNTHETIC.pdf", "doc_type": "cost_report",
         "profile": {"institution": BANK, "jurisdiction": "CH", "period_start": "2025-10-01",
                     "period_end": "2026-09-30"}},
    ]  # fmt: skip
    base = {"measurement": None, "status": "extracted", "fee_code": None, "isin": None}
    facts = [
        base | {"id": 1, "document_id": 1, "key": "p1", "kind": "position", "field": "market_value",
                "label": "Nestle SA", "value": "100000", "currency": "CHF", "isin": "CH0038863350",
                "extra": {}},
        base | {"id": 2, "document_id": 1, "key": "p2", "kind": "position", "field": "market_value",
                "label": "Current account USD", "value": "50000", "currency": "USD",
                "extra": {"asset_class": "CASH"}},
        base | {"id": 3, "document_id": 1, "key": "p3", "kind": "position", "field": "market_value",
                "label": "Current account CHF", "value": "20000", "currency": "CHF",
                "extra": {"asset_class": "CASH"}},
        base | {"id": 4, "document_id": 1, "key": "fx", "kind": "meta", "field": "fx_rate",
                "label": "USD/CHF",
                "value": "0.90", "currency": None, "extra": {}},
        base | {"id": 5, "document_id": 2, "key": "f1", "kind": "fee_observed", "field": "annual_amount",
                "label": "Custody fee", "value": "1000", "currency": "CHF", "fee_code": "CUSTODY_FEE",
                "measurement": "observed", "extra": {}},
    ]  # fmt: skip
    return docs, facts


def _run(rates: dict | None) -> dict:
    return analyse({"domicile": "CH", "cash_rates": rates}, *_pack(), PROPOSAL_DEFAULTS)


def _drag(r: dict, ccy: str) -> dict:
    return next(h for h in r["hidden_costs"] if h["key"].endswith(f"CASH_DRAG:{ccy}"))


def test_cash_drag_is_a_range_per_cash_currency() -> None:
    r = _run(RATES)
    usd = _drag(r, "USD")
    assert usd["status"] == "range" and usd["basis"] == "45000.00"  # USD 50'000 × 0.90
    assert (usd["low"], usd["high"]) == ("0", "1704.74")  # 45'000 × 3.7883%
    assert "SOFR 3.7883%" in usd["method"] and "12 months" in usd["method"]
    chf = _drag(r, "CHF")
    assert (chf["low"], chf["high"]) == ("0", "0.00")  # SARON below zero: no drag
    assert r["hidden_range"] == {"low": "0", "high": "1704.74", "estimated": 2, "not_estimated": 3}


def test_the_range_never_changes_the_totals() -> None:
    with_rates, without = _run(RATES), _run(None)
    assert with_rates["current"]["total_known"] == without["current"]["total_known"] == "1000.00"
    assert with_rates["current"]["is_complete"] == without["current"]["is_complete"]
    assert not any(a["fee_code"] == "CASH_DRAG" for a in with_rates["current"]["atoms"])
    assert with_rates["scenarios"] == without["scenarios"]


def test_without_rates_cash_drag_is_listed_not_estimated() -> None:
    r = _run(None)
    usd = _drag(r, "USD")
    assert usd["status"] == "not_estimated" and usd["low"] is None and usd["high"] is None
    assert r["hidden_range"]["estimated"] == 0


# ------------------------------------------------------------------ SNB client

_CSV = (
    '﻿"CubeId";"zimoma"\r\n"PublishingDate";"2026-11-02 14:30"\r\n\r\n"Date";"D0";"Value"\r\n'
    '"2026-08";"SARON";"-0.06"\r\n"2026-08";"SOFR";"3.60"\r\n"2026-08";"ESTR";"2.00"\r\n'
    '"2026-09";"SARON";"-0.04"\r\n"2026-09";"SOFR";"3.80"\r\n"2026-09";"1TGT";"-0.27"\r\n'
)


def _client(seen: list[httpx.Request], fail: bool = False) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(503) if fail else httpx.Response(200, text=_CSV)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _lookup_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PCE_REFERENCE_FX", "1")  # conftest turns it off; these tests use a mock transport


def test_benchmarks_are_averaged_over_the_published_months(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    out = implicit.benchmark_rates("2026-09-30", _client(seen), tmp_path / "c.json")
    assert out["USD"]["rate_pct"] == "3.7000" and out["USD"]["months"] == ["2026-08", "2026-09", 2]
    assert out["CHF"]["rate_pct"] == "-0.0500"
    assert out["EUR"]["months"][2] == 1
    assert "GBP" not in out  # no SONIA in the answer: no rate, never a guess
    # only a month window is sent
    assert dict(seen[0].url.params) == {"fromDate": "2025-10", "toDate": "2026-09"}


def test_window_is_asked_once_and_errors_are_not_cached(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    cache = tmp_path / "c.json"
    assert implicit.benchmark_rates("2026-09-30", _client(seen, fail=True), cache) == {}
    implicit.benchmark_rates("2026-09-30", _client(seen), cache)
    implicit.benchmark_rates("2026-09-15", _client(seen), cache)  # same 12-month window
    assert len(seen) == 2


def test_client_report_prints_the_hidden_range() -> None:
    import io

    import pdfplumber

    from pce.api import client_safe
    from pce.report import render_client_report

    r = client_safe(_run(RATES))
    r["prospect"] = {"code": "P-SYN", "label": "SYNTHETIC prospect", "synthetic": True}
    r["snapshot_hash"] = "0" * 64
    pdf = render_client_report(r)
    text = " ".join(page.extract_text() or "" for page in pdfplumber.open(io.BytesIO(pdf)).pages)
    assert "Hidden costs, not in the total" in " ".join(text.split())


# ---------------------------------------------------------------- trades (SC-7.23)

NESTLE, ETF = "CH0038863350", "IE00B5BMR087"
REF = {"2026-03-20": {"EUR": {"rate": "1.080000"}, "USD": {"rate": "0.800000"}}}


def _trade(fid: int, side: str, gross: str, ccy: str, isin: str | None = None, **extra) -> dict:
    return {"id": fid, "document_id": 3, "key": f"trade:{fid}", "kind": "transaction",
            "field": "gross_amount",
            "label": "SYNTHETIC trade", "value": gross, "currency": ccy, "isin": isin, "fee_code": None,
            "measurement": "observed", "status": "extracted",
            "extra": {"booking_date": "2026-03-20", "side": side, "quantity": None, **extra}}  # fmt: skip


def _with_trades(trades: list[dict], start: str = "2025-10-01", ref: dict = REF) -> dict:
    docs, facts = _pack()
    docs.append({"id": 3, "filename": "transactions-SYNTHETIC.pdf", "doc_type": "cash_statement",
                 "profile": {"institution": BANK, "jurisdiction": "CH", "period_start": start,
                             "period_end": "2026-09-30"}})  # fmt: skip
    return analyse({"domicile": "CH", "reference_fx": ref}, docs, facts + trades, PROPOSAL_DEFAULTS)


def _hidden(r: dict, code: str) -> dict:
    return next(h for h in r["hidden_costs"] if h["fee_code"] == code)


def test_fx_conversion_above_the_reference_rate_is_the_margin() -> None:
    r = _with_trades([_trade(50, "fx", "100000", "EUR", pair=["EUR", "CHF"], rate="1.0850")])
    h = _hidden(r, "FX_MARGIN")
    assert (h["status"], h["low"], h["high"]) == ("range", "500.00", "500.00")  # (1.0850 − 1.0800) × 100'000
    assert "ECB reference" in h["method"] and "a year" in h["method"]


def test_cross_pair_margin_is_converted_to_chf() -> None:
    # EUR/USD at 1.36 vs reference 1.08 / 0.80 = 1.35: 0.01 USD × 10'000 = 100 USD = 80 CHF
    r = _with_trades([_trade(50, "fx", "10000", "EUR", pair=["EUR", "USD"], rate="1.3600")])
    assert _hidden(r, "FX_MARGIN")["high"] == "80.00"


def test_swiss_stamp_duty_is_the_clients_half_of_the_transfer_tax() -> None:
    r = _with_trades([_trade(50, "buy", "100000", "CHF", NESTLE), _trade(51, "sell", "100000", "USD", ETF)])
    h = _hidden(r, "STAMP_DUTY_CH")
    assert h["high"] == "195.00"  # 100'000 × 0.075% + 80'000 CHF × 0.15%
    assert r["hidden_range"]["high"] == "195.00"  # beside the totals, never in them


def test_half_a_year_of_trades_is_annualised_and_a_short_list_is_a_lower_bound() -> None:
    half = _with_trades([_trade(50, "buy", "100000", "CHF", NESTLE)], start="2026-04-01")
    assert _hidden(half, "STAMP_DUTY_CH")["high"] == str((Decimal(75) * 365 / 183).quantize(Decimal("0.01")))
    short = _with_trades([_trade(50, "buy", "100000", "CHF", NESTLE)], start="2026-09-20")
    assert _hidden(short, "STAMP_DUTY_CH")["high"] == "75.00"
    assert "lower bound" in _hidden(short, "STAMP_DUTY_CH")["method"]


def test_without_rate_or_reference_the_rows_stay_not_estimated_and_totals_never_move() -> None:
    r = _with_trades([_trade(50, "fx", "100000", "EUR", pair=["EUR", "CHF"]), _trade(51, "buy", "5", "CHF")])
    assert _hidden(r, "FX_MARGIN")["status"] == "not_estimated"
    assert _hidden(r, "STAMP_DUTY_CH")["status"] == "not_estimated"  # a buy without ISIN: no estimate
    none = _with_trades([_trade(50, "buy", "100000", "CHF", NESTLE)], ref={})
    assert _hidden(none, "STAMP_DUTY_CH")["high"] == "75.00"  # CHF needs no rate
    assert _hidden(_with_trades([_trade(50, "sell", "1", "USD", ETF)], ref={}), "STAMP_DUTY_CH")[
        "status"
    ] == ("not_estimated")
    docs, facts = _pack()
    assert (
        r["current"]
        == analyse({"domicile": "CH", "reference_fx": REF}, docs, facts, PROPOSAL_DEFAULTS)["current"]
    )


def test_a_stamp_duty_already_debited_is_not_estimated_again() -> None:
    debit = {"id": 60, "document_id": 3, "key": "debit:x", "kind": "cash_debit", "field": "debit_amount",
             "label": "Eidg. Umsatzabgabe", "value": "75.00", "currency": "CHF", "isin": None,
             "fee_code": "STAMP_DUTY_CH", "measurement": "observed", "status": "extracted",
             "extra": {"booking_date": "2026-03-20"}}  # fmt: skip
    r = _with_trades([_trade(50, "buy", "100000", "CHF", NESTLE), debit])
    assert not [h for h in r["hidden_costs"] if h["fee_code"] == "STAMP_DUTY_CH"]


def test_fx_line_reads_amount_and_applied_rate_in_either_order() -> None:
    from test_transactions import _page

    from pce.extraction.models import DocType, DocumentProfile
    from pce.extraction.parsers import parse_cash_statement

    prof = DocumentProfile(doc_type=DocType.CASH_STATEMENT, type_score=3, currency="CHF")
    for row in (["20.03.2026", "FX spot EUR/CHF", "100'000.00", "1.0850", "108'500.00"],
                ["20.03.2026", "Cambio valuta EUR/CHF", "108'500.00", "1.0850", "100'000.00"]):  # fmt: skip
        [f] = parse_cash_statement(_page([row]), prof)
        assert (f.kind, f.value, f.currency, f.extra["rate"], f.extra["pair"]) == (
            "transaction",
            "100000.00",
            "EUR",
            "1.0850",
            ["EUR", "CHF"],
        )


def test_a_eurobond_trade_pays_no_swiss_stamp_duty() -> None:
    r = _with_trades([_trade(50, "buy", "100000", "CHF", "XS0000000009")])
    assert _hidden(r, "STAMP_DUTY_CH")["high"] == "0.00"
