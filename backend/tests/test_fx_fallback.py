"""SC-7.11: reference FX fallback. All data here is SYNTHETIC; the ECB is replaced by a mock transport."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.finance import fx

BANK = "Synthetic Bank SA"
ETF_USD = "IE00B5BMR087"
REF = {"2026-09-30": {"USD": {"rate": "0.833011", "rate_date": "2026-09-30", "source": fx.SOURCE,
                              "url": fx.ECB_URL.format(ccys="USD")}}}  # fmt: skip


def _pack(printed_rate: str | None = None) -> tuple[list[dict], list[dict]]:
    docs = [
        {"id": 1, "filename": "statement-SYNTHETIC.pdf", "doc_type": "portfolio_statement",
         "profile": {"institution": BANK, "jurisdiction": "CH", "as_of": "2026-09-30"}},
        {"id": 2, "filename": "costs-SYNTHETIC.pdf", "doc_type": "cost_report",
         "profile": {"institution": BANK, "jurisdiction": "CH", "period_start": "2025-10-01",
                     "period_end": "2026-09-30"}},
        {"id": 3, "filename": "kid-SYNTHETIC.pdf", "doc_type": "kid", "profile": {"as_of": "2026-03-01"}},
    ]  # fmt: skip
    base = {"measurement": None, "status": "extracted", "extra": {}, "fee_code": None, "isin": None}
    facts = [
        base | {"id": 1, "document_id": 1, "key": "p1", "kind": "position", "field": "market_value",
                "label": "S&P 500 UCITS ETF", "value": "100000", "currency": "USD", "isin": ETF_USD},
        base | {"id": 2, "document_id": 1, "key": "p2", "kind": "position", "field": "market_value",
                "label": "Nestle SA", "value": "50000", "currency": "CHF", "isin": "CH0038863350"},
        base | {"id": 3, "document_id": 2, "key": "f1", "kind": "fee_observed", "field": "annual_amount",
                "label": "Custody fee", "value": "300", "currency": "USD", "fee_code": "CUSTODY_FEE",
                "measurement": "observed"},
        base | {"id": 4, "document_id": 3, "key": "k1", "kind": "product_cost", "field": "rate_pct",
                "label": "Ongoing", "value": "0.10", "currency": None, "isin": ETF_USD,
                "fee_code": "FUND_ONGOING", "measurement": "estimated"},
    ]  # fmt: skip
    if printed_rate:
        facts.append(base | {"id": 5, "document_id": 1, "key": "fx", "kind": "meta", "field": "fx_rate",
                             "label": "USD/CHF", "value": printed_rate, "currency": None})  # fmt: skip
    return docs, facts


def _run(ref: dict, printed_rate: str | None = None) -> dict:
    return analyse({"domicile": "CH", "reference_fx": ref}, *_pack(printed_rate), PROPOSAL_DEFAULTS)


def _check(r: dict, prefix: str) -> dict | None:
    return next((c for c in r["checks"] if c["key"].startswith(prefix)), None)


def test_usd_position_without_printed_rate_is_valued_at_the_reference_rate() -> None:
    r = _run(REF)
    assert r["aum"]["total"] == "133301.10"  # 100'000 × 0.833011 + 50'000
    [ocf] = [a for a in r["current"]["atoms"] if a["fee_code"] == "FUND_ONGOING"]
    assert ocf["amount"] == "83.30" and ocf["role"] == "counted"
    [custody] = [a for a in r["current"]["atoms"] if a["fee_code"] == "CUSTODY_FEE"]
    assert custody["amount"] == "249.90" and "ECB euro reference rate, 2026-09-30" in custody["formula"]
    c = _check(r, "fx_ref:")
    assert c["status"] == "info" and "data-api.ecb.europa.eu" in c["detail"]
    assert _check(r, "fx_missing:") is None


def test_printed_rate_wins_over_the_reference_rate() -> None:
    r = _run(REF, printed_rate="0.8300")
    assert r["aum"]["total"] == "133000.00"
    assert _check(r, "fx_ref:") is None
    assert _check(r, "fx_gap:") is None  # 0.8300 vs 0.833011: within 1%


def test_printed_rate_far_from_reference_is_a_review_point() -> None:
    r = _run(REF, printed_rate="0.9300")  # a misread 8 → 9
    assert r["aum"]["total"] == "143000.00"
    assert _check(r, "fx_gap:")["status"] == "warn"


def test_without_any_rate_the_position_stays_unvalued() -> None:
    r = _run({})
    assert r["aum"]["total"] == "50000"
    assert _check(r, "fx_missing:")["status"] == "fail"
    assert all(a["role"] == "unknown" for a in r["current"]["atoms"] if a["fee_code"] == "FUND_ONGOING")


# ------------------------------------------------------------------ ECB client


@pytest.fixture(autouse=True)
def _lookup_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PCE_REFERENCE_FX", "1")  # conftest turns it off; these tests use a mock transport


_CSV = (
    "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
    "EXR.D.CHF.EUR.SP00.A,D,CHF,EUR,SP00,A,2026-09-24,0.9400,\n"
    "EXR.D.CHF.EUR.SP00.A,D,CHF,EUR,SP00,A,2026-09-25,0.9478,\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-09-24,1.1000,\n"
    "EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-09-25,1.1378,\n"
)


def _client(seen: list[httpx.Request], fail: bool = False) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(503) if fail else httpx.Response(200, text=_CSV)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cross_rate_through_eur_on_the_last_fixing_before_a_weekend(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    out = fx.reference_rates({"2026-09-27": {"USD", "EUR"}}, "CHF", _client(seen), tmp_path / "c.json")
    usd = out["2026-09-27"]["USD"]
    assert Decimal(usd["rate"]) == (Decimal("0.9478") / Decimal("1.1378")).quantize(Decimal("0.000001"))
    assert usd["rate_date"] == "2026-09-25"  # Sunday asks for Friday's fixing
    assert out["2026-09-27"]["EUR"]["rate"] == "0.947800"
    # only currency codes and dates leave the machine
    assert len(seen) == 1
    assert seen[0].url.path.endswith("/D.CHF+USD.EUR.SP00.A")
    assert set(seen[0].url.params) == {"startPeriod", "endPeriod", "format"}


def test_rates_are_cached_so_a_date_is_asked_once(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    cache = tmp_path / "c.json"
    first = fx.reference_rates({"2026-09-27": {"USD"}}, "CHF", _client(seen), cache)
    again = fx.reference_rates({"2026-09-27": {"USD"}}, "CHF", _client(seen), cache)
    assert first == again and len(seen) == 1


def test_unquoted_currency_and_network_error_give_no_rate(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    assert fx.reference_rates({"2026-09-27": {"XAU"}}, "CHF", _client(seen), tmp_path / "a.json") == {}
    assert fx.reference_rates({"2026-09-27": {"USD"}}, "CHF", _client(seen, True), tmp_path / "b.json") == {}


def test_lookup_off_by_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PCE_REFERENCE_FX", "0")
    seen: list[httpx.Request] = []
    assert fx.reference_rates({"2026-09-27": {"USD"}}, "CHF", _client(seen), tmp_path / "c.json") == {}
    assert seen == []
