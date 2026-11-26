"""Implicit costs estimated from data, shown as a range and never added to a total (SC-7.14).

Cash drag: cash earns the interest the bank credits, which is somewhere between nothing and the market
rate. With the credited rate unknown, the yearly cost of holding the cash is a range with no assumption in
it: from 0 (the bank pays the market rate) to market rate x cash (the bank pays nothing). The market rate is
the overnight benchmark of the cash currency (SARON, ESTR, SOFR, SONIA, TONA), averaged over the 12 months
up to the valuation date. A negative benchmark gives no drag.

The benchmark averages come from the SNB data portal (cube ``zimoma``, monthly averages), the same host as
the approved SNB reference rates (Ale, 2026-11-25 and 2026-11-26). The request carries no client data, only
a month range. Answers are cached on disk; ``PCE_REFERENCE_FX=0`` turns this lookup off too.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import threading
from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx

from .fx import enabled
from .money import ZERO, D

log = logging.getLogger(__name__)

SNB_URL = "https://data.snb.ch/api/cube/zimoma/data/csv/en"
SOURCE = "SNB data portal, money market rates (zimoma), monthly averages"
BENCHMARK = {"CHF": "SARON", "EUR": "ESTR", "USD": "SOFR", "GBP": "SONIA", "JPY": "TONA"}
MONTHS = 12
TIMEOUT = 10.0
_LOCK = threading.Lock()


def _month(d: date, back: int) -> str:
    y, m = divmod(d.year * 12 + d.month - 1 - back, 12)
    return f"{y:04d}-{m + 1:02d}"


def _fetch(client: httpx.Client, first: str, last: str) -> dict[str, dict[str, Decimal]]:
    """{benchmark: {month: percent}} from the SNB CSV (a few header lines, then Date;D0;Value)."""
    r = client.get(SNB_URL, params={"fromDate": first, "toDate": last})
    r.raise_for_status()
    body = r.text.replace("\r\n", "\n").split("\n\n", 1)[-1]
    out: dict[str, dict[str, Decimal]] = {}
    for row in csv.DictReader(io.StringIO(body), delimiter=";"):
        if row.get("Value"):
            out.setdefault(row["D0"], {})[row["Date"]] = D(row["Value"])
    return out


def _cache_path() -> Path:
    from ..db import data_dir

    return data_dir() / "money_market_rates.json"


def benchmark_rates(
    as_of: str, client: httpx.Client | None = None, cache: Path | None = None
) -> dict[str, dict]:
    """Average benchmark per currency over the 12 months up to ``as_of``.

    {ccy: {benchmark, rate_pct, months: [first, last, count], source, url}}. A currency with no published
    month in the window is absent; so is everything after a network error.
    """
    if not enabled():
        return {}
    d = date.fromisoformat(as_of)
    first, last = _month(d, MONTHS - 1), _month(d, 0)
    key = f"{first}:{last}"
    path = cache or _cache_path()
    with _LOCK:
        known: dict[str, dict] = json.loads(path.read_text()) if path.exists() else {}
    if key not in known:
        own = client is None
        client = client or httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "FeeLens money market rates"})
        try:
            series = _fetch(client, first, last)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            log.warning("money market rates lookup failed: %s", type(exc).__name__)
            return {}
        finally:
            if own:
                client.close()
        out = {}
        for ccy, name in BENCHMARK.items():
            months = sorted(series.get(name, {}))
            if not months:
                continue
            avg = sum((series[name][m] for m in months), ZERO) / len(months)
            out[ccy] = {
                "benchmark": name,
                "rate_pct": str(avg.quantize(Decimal("0.0001"))),
                "months": [months[0], months[-1], len(months)],
                "source": SOURCE,
                "url": f"{SNB_URL}?fromDate={first}&toDate={last}",
            }
        known[key] = out
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(known, indent=1, sort_keys=True))
    return known[key]


def cash_drag_range(cash: Decimal, benchmark_pct: Decimal) -> tuple[Decimal, Decimal]:
    """Yearly cost of holding ``cash``: 0 if the bank pays the benchmark, benchmark x cash if it pays 0."""
    return ZERO, max(ZERO, benchmark_pct) * cash / Decimal(100)
