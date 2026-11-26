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
