# ruff: noqa: E501
"""SC-6.3: holding type from public registers, sending ISINs only. No network: httpx.MockTransport."""

from __future__ import annotations

import json

import httpx
import pytest

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS
from pce.instruments import registry

FUND = "FR0000284341"  # not in FIRDS in this fake: OpenFIGI answers
ETF = "IE00B4L5Y983"
SHARE = "CH0038863350"


def _transport(seen: list[httpx.Request], fail: bool = False) -> httpx.MockTransport:
    cfi = {ETF: "CEOGES", SHARE: "ESVTFR"}

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if fail:
            raise httpx.ConnectError("offline")
        if req.url.host == "registers.esma.europa.eu":
            isin = req.url.params["q"].removeprefix("isin:")
            docs = [{"isin": isin, "gnr_cfi_code": cfi[isin]}] if isin in cfi else []
            return httpx.Response(200, json={"response": {"docs": docs}})
        assert req.url.host == "api.openfigi.com"
        body = json.loads(req.content)
        return httpx.Response(
            200,
            json=[{"data": [{"securityType2": "Mutual Fund", "marketSector": "Equity"}]} for _ in body],
        )

    return httpx.MockTransport(handle)


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("PCE_PUBLIC_ISIN_LOOKUP", "1")


def test_types_come_from_firds_then_openfigi(tmp_path) -> None:
    seen: list[httpx.Request] = []
    got = registry.resolve([ETF, SHARE, FUND, "NOTANISIN"], httpx.Client(transport=_transport(seen)),
                           tmp_path / "c.json")  # fmt: skip
    assert {k: v["asset_class"] for k, v in got.items()} == {ETF: "ETF", SHARE: "EQUITY", FUND: "FUND"}
    assert got[FUND]["source"] == "OpenFIGI" and got[ETF]["source"] == "ESMA FIRDS"


def test_only_isins_leave_the_machine_and_each_is_asked_once(tmp_path) -> None:
    seen: list[httpx.Request] = []
    client = httpx.Client(transport=_transport(seen))
    registry.resolve([ETF, FUND], client, tmp_path / "c.json")
    for req in seen:
        assert req.url.host in {"registers.esma.europa.eu", "api.openfigi.com"}
        sent = dict(req.url.params) | ({"body": json.loads(req.content)} if req.content else {})
        text = json.dumps(sent)
        assert all(x not in text for x in ("value", "quantity", "name", "CHF"))
    n = len(seen)
    registry.resolve([ETF, FUND], client, tmp_path / "c.json")
    assert len(seen) == n  # cached


def test_offline_falls_back_and_asks_again_later(tmp_path) -> None:
    seen: list[httpx.Request] = []
    cache = tmp_path / "c.json"
    assert registry.resolve([ETF], httpx.Client(transport=_transport(seen, fail=True)), cache) == {}
    assert (
        registry.resolve([ETF], httpx.Client(transport=_transport(seen)), cache)[ETF]["asset_class"] == "ETF"
    )


def test_switched_off_sends_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PCE_PUBLIC_ISIN_LOOKUP", "0")
    seen: list[httpx.Request] = []
    assert registry.resolve([ETF], httpx.Client(transport=_transport(seen)), tmp_path / "c.json") == {}
    assert seen == []


@pytest.mark.parametrize(("cfi", "cls"), [("ESVUFR", "EQUITY"), ("CIOGLS", "FUND"), ("CEOGES", "ETF"),
                                          ("DBFTFB", "BOND"), ("DEMXXX", "STRUCTURED"), ("RWSNCA", "STRUCTURED")])  # fmt: skip
def test_cfi_codes(cfi: str, cls: str) -> None:
    assert registry.class_from_cfi(cfi) == cls


def test_fund_named_like_a_company_without_kid_is_an_unknown_cost_not_zero() -> None:
    docs = [
        {
            "id": 1,
            "filename": "assets.pdf",
            "doc_type": "portfolio_statement",
            "profile": {"institution": "Synthetic Bank", "jurisdiction": "CH", "currency": "CHF"},
        }
    ]
    pos = {"id": 1, "document_id": 1, "key": f"position:{FUND}", "kind": "position", "field": "market_value",
           "label": "Comgest Monde C", "value": "150000.00", "currency": "CHF", "isin": FUND, "fee_code": None,
           "measurement": None, "status": "extracted"}  # fmt: skip
    by_name = analyse({"domicile": "CH"}, docs, [{**pos, "extra": {}}], PROPOSAL_DEFAULTS)
    by_register = analyse(
        {"domicile": "CH"}, docs, [{**pos, "extra": {"asset_class": "FUND"}}], PROPOSAL_DEFAULTS
    )

    def gap(r: dict) -> list[dict]:
        return [
            a for a in r["current"]["atoms"] if a["instrument_id"] == FUND and a["fee_code"] == "FUND_ONGOING"
        ]

    assert gap(by_name) == []  # the name rule calls it a share: no cost asked for
    [atom] = gap(by_register)
    assert atom["measurement"] == "unknown" and atom["amount"] is None
