"""Real public instruments the SYNTHETIC statements hold.

Funds and ETFs come from the specimen corpus (``data/reference/specimen_corpus.csv``): each has a public
KID fetched from its issuer and a hand-checked ongoing charge, so a statement that holds it can be joined
to that real KID end to end. Stocks and bonds were checked against OpenFIGI on 2026-11-25 (name and
security type, ISIN sent alone). Prices are illustrative round numbers, not market data: a statement
says SYNTHETIC on every page, and only the identifiers are real.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
CORPUS_CSV = ROOT / "data" / "reference" / "specimen_corpus.csv"


@dataclass(frozen=True)
class Instrument:
    isin: str
    name: str
    kind: str  # EQUITY | BOND | ETF | FUND
    currency: str
    price: Decimal  # illustrative; a bond's price is in percent of nominal
    ocf_pct: Decimal | None = None  # hand-checked ongoing charge from the real KID (funds and ETFs)
    kid_file: str | None = None  # specimen file name under var/specimens


# OpenFIGI check 2026-11-25: every ISIN maps to the named issuer and security type.
STOCKS = [
    Instrument("CH0038863350", "Nestle SA Reg", "EQUITY", "CHF", Decimal("88.40")),
    Instrument("CH0012005267", "Novartis AG Reg", "EQUITY", "CHF", Decimal("92.15")),
    Instrument("CH0012032048", "Roche Holding AG Genussschein", "EQUITY", "CHF", Decimal("256.80")),
    Instrument("CH0244767585", "UBS Group AG Reg", "EQUITY", "CHF", Decimal("27.35")),
    Instrument("CH0011075394", "Zurich Insurance Group AG", "EQUITY", "CHF", Decimal("531.00")),
    Instrument("CH0012221716", "ABB Ltd Reg", "EQUITY", "CHF", Decimal("47.62")),
    Instrument("CH0210483332", "Cie Financiere Richemont A Reg", "EQUITY", "CHF", Decimal("142.25")),
    Instrument("CH0418792922", "Sika AG Reg", "EQUITY", "CHF", Decimal("218.40")),
    Instrument("CH0013841017", "Lonza Group AG Reg", "EQUITY", "CHF", Decimal("540.60")),
    Instrument("CH0025751329", "Logitech International SA Reg", "EQUITY", "CHF", Decimal("71.30")),
    Instrument("US0378331005", "Apple Inc", "EQUITY", "USD", Decimal("228.50")),
    Instrument("US5949181045", "Microsoft Corp", "EQUITY", "USD", Decimal("415.20")),
    Instrument("US0231351067", "Amazon.com Inc", "EQUITY", "USD", Decimal("186.75")),
    Instrument("US02079K3059", "Alphabet Inc Class A", "EQUITY", "USD", Decimal("163.40")),
    Instrument("DE0007164600", "SAP SE", "EQUITY", "EUR", Decimal("231.90")),
    Instrument("FR0000121014", "LVMH Moet Hennessy Louis Vuitton SE", "EQUITY", "EUR", Decimal("612.30")),
    Instrument("NL0010273215", "ASML Holding NV", "EQUITY", "EUR", Decimal("648.10")),
    Instrument("IT0003132476", "Eni SpA", "EQUITY", "EUR", Decimal("13.82")),
    Instrument("IT0003128367", "Enel SpA", "EQUITY", "EUR", Decimal("7.12")),
    Instrument("IT0000072618", "Intesa Sanpaolo SpA", "EQUITY", "EUR", Decimal("4.05")),
]
BONDS = [
    Instrument("CH0224397213", "0.5% Swiss Confederation 2014-27.05.2030", "BOND", "CHF", Decimal("100.85")),
    Instrument("CH0344958688", "0.5% Swiss Confederation 2016-27.06.2032", "BOND", "CHF", Decimal("100.40")),
    Instrument("CH0127181193", "1.25% Swiss Confederation 2011-27.06.2037", "BOND", "CHF", Decimal("106.20")),
    Instrument("IT0005436693", "0.6% BTP 2021-01.08.2031", "BOND", "EUR", Decimal("88.75")),
    Instrument("IT0005383309", "1.35% BTP 2019-01.04.2030", "BOND", "EUR", Decimal("95.60")),
    Instrument("IT0005425233", "1.7% BTP 2020-01.09.2051", "BOND", "EUR", Decimal("61.30")),
    Instrument(
        "DE0001102580", "0% Bundesrepublik Deutschland 2022-15.02.2032", "BOND", "EUR", Decimal("86.45")
    ),
    Instrument(
        "DE0001102614", "1.8% Bundesrepublik Deutschland 2023-15.08.2053", "BOND", "EUR", Decimal("78.10")
    ),
    Instrument("US91282CJZ59", "4% US Treasury Note 2024-15.02.2034", "BOND", "USD", Decimal("98.20")),
]

_KID_WORDS = re.compile(
    r"key information|basisinformationsblatt|documento contenente|document d.informations|"
    r"informations cl|^kid\b|^dic\b|^kiid\b|informazioni chiave",
    re.I,
)
_OCF = re.compile(r"FUND_ONGOING=([0-9.]+)")


def _fund_name(title: str) -> str:
    parts = [p.strip() for p in re.split(r"\s[–-]\s", title) if p.strip()]
    keep = [p for p in parts if not _KID_WORDS.search(p)] or parts
    name = keep[0]
    if len(name) < 14 and len(keep) > 1:  # "Nordea 1 - European Covered Bond Fund": the dash is in the name
        name = f"{name} - {keep[1]}"
    name = re.sub(r"\((?:Swiss|CH)[^)]*\)", "", name).strip()
    name = re.sub(r"^(?:KID|DIC|KIID)\s+", "", name)
    return name[:60]


def _price_for(isin: str) -> Decimal:
    """Deterministic illustrative NAV between 20 and 220 from the ISIN, two decimals."""
    n = sum((i + 1) * ord(c) for i, c in enumerate(isin))
    return Decimal(20 + n % 200) + Decimal(n % 97) / 100


def funds() -> list[Instrument]:
    """One instrument per distinct ISIN with a hand-checked ongoing charge, in manifest order."""
    out: dict[str, Instrument] = {}
    with CORPUS_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m = _OCF.search(r["expected"])
            if (
                not (r["document_type"].startswith("kid") and r["isin"] and m)
                or ";" in r["isin"]
                or r["isin"] in out
            ):
                continue
            kind = "ETF" if r["product"] == "etf" or "ETF" in r["title"] else "FUND"
            ccy = "CHF" if r["isin"].startswith("CH") else ("USD" if r["isin"].startswith("IE") else "EUR")
            out[r["isin"]] = Instrument(
                r["isin"], _fund_name(r["title"]), kind, ccy, _price_for(r["isin"]),
                Decimal(m.group(1)), r["file"],
            )  # fmt: skip
    return list(out.values())


def universe() -> list[Instrument]:
    return [*STOCKS, *BONDS, *funds()]
