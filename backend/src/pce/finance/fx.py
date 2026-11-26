"""Reference exchange rates for amounts whose documents print no rate (SC-7.11).

A USD position without a printed USD/CHF rate used to stay unvalued: out of the asset base, its product
costs unknown. The fallback is the ECB euro reference rate on (or before) the valuation date, crossed
through EUR: CHF per USD = (CHF per EUR) / (USD per EUR). A rate printed on the client's own documents
always wins; the analysis flags a reference rate that differs from it.

Privacy (ADR 0004, approved by Ale 2026-11-25): the request carries currency codes and a date only, never
client data. Answers are cached on disk, so a date is asked once. Any network error returns no rate and the
amount stays unconverted, as before. ``PCE_REFERENCE_FX=0`` turns the lookup off.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import threading
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

from .money import D

log = logging.getLogger(__name__)

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.{ccys}.EUR.SP00.A"
SOURCE = "ECB euro reference rate"
LOOKBACK_DAYS = 7  # weekends and TARGET holidays have no fixing: take the last one before the date
TIMEOUT = 10.0
_LOCK = threading.Lock()


def enabled() -> bool:
    return os.environ.get("PCE_REFERENCE_FX", "1") != "0"


def cross(ccy: str, base: str, per_eur: dict[str, Decimal]) -> Decimal | None:
    """Units of ``base`` for one ``ccy``, from ECB quotes (units of a currency per 1 EUR)."""
    quotes = {**per_eur, "EUR": Decimal(1)}
    if ccy not in quotes or base not in quotes:
        return None
    return quotes[base] / quotes[ccy]


def _fetch(client: httpx.Client, day: date, ccys: list[str]) -> dict[str, tuple[Decimal, str]]:
    """Last ECB quote per currency on or before ``day``: {ccy: (units per EUR, quote date)}."""
    url = ECB_URL.format(ccys="+".join(ccys))
    params = {
        "startPeriod": (day - timedelta(days=LOOKBACK_DAYS)).isoformat(),
        "endPeriod": day.isoformat(),
        "format": "csvdata",
    }
    r = client.get(url, params=params)
    r.raise_for_status()
    out: dict[str, tuple[Decimal, str]] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        if row.get("OBS_VALUE") and row["TIME_PERIOD"] >= out.get(row["CURRENCY"], (0, ""))[1]:
            out[row["CURRENCY"]] = (D(row["OBS_VALUE"]), row["TIME_PERIOD"])
    return out


def _cache_path() -> Path:
    from ..db import data_dir

    return data_dir() / "reference_fx.json"


def reference_rates(
    needs: dict[str, set[str]],
    base: str = "CHF",
    client: httpx.Client | None = None,
    cache: Path | None = None,
) -> dict[str, dict[str, dict]]:
    """Rates to ``base`` per valuation date: {date: {ccy: {rate, rate_date, source, url}}}.

    ``needs`` maps an ISO valuation date to the currencies to convert. A currency the ECB does not quote
    (or a failed request) is simply absent: the caller keeps the amount unconverted.
    """
    if not enabled():
        return {}
    path = cache or _cache_path()
    with _LOCK:
        known: dict[str, dict] = json.loads(path.read_text()) if path.exists() else {}
    out: dict[str, dict[str, dict]] = {}
    own = client is None
    todo = {
        day: sorted(c for c in ccys if c != base and c.isalpha() and len(c) == 3)
        for day, ccys in needs.items()
    }
    try:
        for day, ccys in sorted(todo.items()):
            missing = [c for c in ccys if f"{day}:{c}:{base}" not in known]
            if missing:
                client = client or httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "FeeLens FX rates"})
                asked = sorted({*missing, base} - {"EUR"})
                quotes = _fetch(client, date.fromisoformat(day), asked)
                per_eur = {c: q for c, (q, _d) in quotes.items()}
                for c in missing:
                    rate = cross(c, base, per_eur)
                    when = max((quotes[x][1] for x in (c, base) if x in quotes), default=None)
                    # an unquoted currency is cached as None so it is not asked again
                    known[f"{day}:{c}:{base}"] = (
                        {
                            "rate": str(rate.quantize(Decimal("0.000001"))),
                            "rate_date": when,
                            "source": SOURCE,
                            "url": ECB_URL.format(ccys=base if c == "EUR" else c),
                        }
                        if rate is not None
                        else None
                    )
            for c in ccys:
                if hit := known.get(f"{day}:{c}:{base}"):
                    out.setdefault(day, {})[c] = hit
    except (httpx.HTTPError, ValueError, KeyError) as exc:  # offline or bad answer: stay unconverted
        log.warning("reference fx lookup failed: %s", type(exc).__name__)
    finally:
        if own and client is not None:
            client.close()
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(known, indent=1, sort_keys=True))
    return out
