"""Instrument type from public registers, by ISIN only (SC-6.3).

A holding's type decides whether a missing KID is an unknown product cost or no cost at all. Guessing it
from the name fails on funds named like companies ("Comgest Monde C") and on bonds without a bond word,
so the cost was reported complete while a fund's ongoing charge was missing. The type comes from:

1. ESMA FIRDS: the CFI code of every instrument traded on an EU venue (authoritative).
2. OpenFIGI: security type and market sector for the rest (Swiss-only, US).

Privacy (ADR 0004, approved by Ale 2026-11-25): only ISINs leave the machine, to these two hosts. No
quantity, value, name or account. Answers are cached on disk so an ISIN is asked once. Any network error
returns no answer and the name rule applies, as before. ``PCE_PUBLIC_ISIN_LOOKUP=0`` turns it off.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path

import httpx
from stdnum import isin as stdisin

log = logging.getLogger(__name__)

FIRDS_URL = "https://registers.esma.europa.eu/solr/esma_registers_firds/select"
OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
OPENFIGI_BATCH = 10  # the keyless limit per request
TIMEOUT = 10.0
_LOCK = threading.Lock()


def enabled() -> bool:
    return os.environ.get("PCE_PUBLIC_ISIN_LOOKUP", "1") != "0"


def class_from_cfi(cfi: str) -> str | None:
    """ISO 10962 CFI → the app's asset class."""
    cfi = (cfi or "").upper()
    if cfi.startswith("E"):
        return "EQUITY"
    if cfi.startswith("CE"):
        return "ETF"
    if cfi.startswith("C"):
        return "FUND"
    if cfi.startswith(("DS", "DE", "RW")):  # structured instruments, warrants
        return "STRUCTURED"
    if cfi.startswith("D"):
        return "BOND"
    return None


def class_from_figi(item: dict) -> str | None:
    """OpenFIGI securityType2 / marketSector → the app's asset class."""
    t2 = (item.get("securityType2") or "").lower()
    t1 = (item.get("securityType") or "").lower()
    sector = (item.get("marketSector") or "").lower()
    if t2 == "mutual fund" or "fund" in t1:
        return "FUND"
    if t2 == "etp" or "etf" in t1 or "etp" in t1:
        return "ETF"
    if t2 in ("warrant",) or "structured" in t1 or "certificate" in t1:
        return "STRUCTURED"
    if t2 in ("common stock", "depositary receipt", "preference", "pfd") or (sector == "equity" and not t2):
        return "EQUITY"
    if sector in ("govt", "corp", "muni") or t2 in ("corp", "govt"):
        return "BOND"
    return None


def _firds(client: httpx.Client, isin: str) -> dict | None:
    params = {"q": f"isin:{isin}", "wt": "json", "rows": 1, "fl": "isin,gnr_cfi_code"}
    r = client.get(FIRDS_URL, params=params)
    r.raise_for_status()
    docs = r.json().get("response", {}).get("docs", [])
    cls = class_from_cfi(docs[0].get("gnr_cfi_code", "")) if docs else None
    return {"asset_class": cls, "source": "ESMA FIRDS", "cfi": docs[0]["gnr_cfi_code"]} if cls else None


def _openfigi(client: httpx.Client, isins: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(isins), OPENFIGI_BATCH):
        batch = isins[i : i + OPENFIGI_BATCH]
        r = client.post(OPENFIGI_URL, json=[{"idType": "ID_ISIN", "idValue": x} for x in batch])
        r.raise_for_status()
        for isin, ans in zip(batch, r.json(), strict=True):
            data = ans.get("data") or []
            cls = next((c for c in map(class_from_figi, data) if c), None)
            if cls:
                out[isin] = {"asset_class": cls, "source": "OpenFIGI"}
    return out


def _cache_path() -> Path:
    from ..db import data_dir

    return data_dir() / "instrument_types.json"


def resolve(
    isins: list[str], client: httpx.Client | None = None, cache: Path | None = None
) -> dict[str, dict]:
    """Asset class per ISIN that a register knows: {isin: {asset_class, source, [cfi], date}}."""
    wanted = sorted({x for x in isins if x and stdisin.is_valid(x)})
    if not wanted or not enabled():
        return {}
    path = cache or _cache_path()
    with _LOCK:
        known: dict[str, dict] = json.loads(path.read_text()) if path.exists() else {}
    todo = [x for x in wanted if x not in known]
    if todo:
        found: dict[str, dict] = {}
        complete = False
        own = client is None
        client = client or httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "FeeLens instrument lookup"})
        try:
            for x in todo:
                if hit := _firds(client, x):
                    found[x] = hit
            rest = [x for x in todo if x not in found]
            if rest:
                found |= _openfigi(client, rest)
            complete = True
        except (httpx.HTTPError, ValueError) as exc:  # offline, rate limit, bad JSON: fall back to names
            log.warning("isin lookup failed after %d of %d: %s", len(found), len(todo), type(exc).__name__)
        finally:
            if own:
                client.close()
        today = datetime.now(UTC).date().isoformat()
        for x in todo:  # an ISIN no register knows is cached too (not after an error: it is asked again)
            if x in found or complete:
                known[x] = {**found.get(x, {"asset_class": None, "source": None}), "date": today}
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(known, indent=1, sort_keys=True))
        log.info("isin lookup: %d asked, %d resolved", len(todo), len(found))
    return {x: known[x] for x in wanted if known.get(x, {}).get("asset_class")}
