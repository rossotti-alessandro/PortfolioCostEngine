"""Multilingual vocabulary (EN/DE/FR/IT) for classification and fee-label mapping.

Order matters: more specific patterns come first (e.g. "VAT on fees" before "fees").
Extend here, not in parser code, when a new bank layout uses different wording.
"""

from __future__ import annotations

import re

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "kid": [
        "key information document",
        "basisinformationsblatt",
        "documento contenente le informazioni chiave",
        "document d'informations clés",
        "composition of costs",
    ],
    "termsheet": [
        "termsheet",
        "term sheet",
        "final terms",
        "endgültige bedingungen",
        "condizioni definitive",
    ],
    "cost_report": [
        "costs and charges",
        "kosten und gebühren",
        "costi e oneri",
        "coûts et frais",
        "ex-post",
        "ausweis über kosten",
        "report on costs",
    ],
    "tariff": [
        "price schedule",
        "schedule of prices",
        "tariff",
        "preisliste",
        "tariffario",
        "conditions tarifaires",
        "fee agreement",
        "valid from",
        "dienstleistungspreise",
        "preisübersicht",
        "servizi e prezzi",
        "prices and services",
    ],
    "cash_statement": [
        "estratto conto",
        "account statement",
        "kontoauszug",
        "relevé de compte",
        "movimenti",
        "transactions",
    ],
    "portfolio_statement": [
        "statement of assets",
        "vermögensausweis",
        "relevé de fortune",
        "estratto patrimoniale",
        "holdings report",
        "situazione patrimoniale",
        "dossier titoli",
        "controvalore",
        "open positions",
        "positions",
        "market value",
    ],
}

FEE_LABELS: list[tuple[str, re.Pattern[str]]] = [
    ("VAT_ON_FEES", re.compile(r"\b(vat|mwst|iva|tva)\b", re.I)),
    (
        "STAMP_DUTY_CH",
        re.compile(r"stamp duty|umsatzabgabe|tassa di bollo|droit de timbre|eidg\. abgabe", re.I),
    ),
    ("FX_COMMISSION", re.compile(r"foreign exchange|\bfx\b|devisen|cambi|opérations de change", re.I)),
    (
        "BROKERAGE",
        re.compile(
            r"brokerage|courtage|intermediazione|negoziazione|transaction fee|transaktionsgebühr|"
            r"^commissions?$",
            re.I,
        ),
    ),
    ("ACCOUNT_FEE", re.compile(r"tenuta conto|account maintenance|kontoführung|tenue de compte", re.I)),
    ("PLATFORM_FIXED", re.compile(r"market data|subscription|abbonament|platform fee|plattformgebühr", re.I)),
    (
        "CUSTODY_FEE",
        re.compile(r"custody|safekeeping|depotgebühr|custodia|droits? de garde|frais de garde", re.I),
    ),
    ("ALL_IN_FEE", re.compile(r"all[- ]in|forfettari|pauschal|forfait", re.I)),
    ("ADVISORY_FEE", re.compile(r"advisory|consulenza|beratung|frais de conseil", re.I)),
    (
        "MGMT_DISCRETIONARY",
        re.compile(
            r"management fee|mandate fee|gestione patrimoniale|commissione di gestione|"
            r"verwaltungs|mandatsgebühr|"
            r"frais de gestion|commission de gestion",
            re.I,
        ),
    ),
]


def load_taxonomy(name: str, folder: str = "taxonomy") -> list[dict[str, str]]:
    """Rows of data/<folder>/<name>.csv (taxonomy: the research source of truth), or [] if absent."""
    import csv
    from pathlib import Path

    for parent in Path(__file__).resolve().parents:
        f = parent / "data" / folder / f"{name}.csv"
        if f.exists():
            with f.open(encoding="utf-8-sig") as fh:
                return list(csv.DictReader(fh))
    return []


FEE_LABEL_NAMES = {r["fee_code"]: r["label_en"] for r in load_taxonomy("fee_taxonomy")}

QUARTER_WORDS = re.compile(r"trimestre|quarter|quartal|vierteljahr", re.I)
JURISDICTION_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("LU", re.compile(r"luxembourg|luxemburg|lussemburgo", re.I)),
    ("LI", re.compile(r"liechtenstein|vaduz", re.I)),
    (
        "CH",
        re.compile(
            r"switzerland|schweiz|svizzera|suisse|lugano|locarno|bellinzona|chiasso|zurich|zürich|geneva|genève|"
            r"basel|\bbern\b|luzern|st\. ?gallen",
            re.I,
        ),
    ),
    ("IT", re.compile(r"\bitalia\b|\bitaly\b|\bmilano\b|\bmilan\b|\broma\b|\btorino\b", re.I)),
    ("US", re.compile(r"united states|new york|\busa\b", re.I)),
]
FX_RATE = re.compile(
    r"(?:fx rate|exchange rate|tasso di cambio|cambio|wechselkurs|devisenkurs|taux de change)\s+"
    r"([A-Z]{3})\s*/\s*([A-Z]{3})\b[^:]*:\s*([0-9][0-9.,']*)",
    re.I,
)
FEE_SECTION = re.compile(
    r"fees and commissions|commissioni e spese|gebühren und kommissionen|frais et commissions", re.I
)
LANG_HINTS = {
    "it": re.compile(r"\b(periodo|conto|cliente|commissione|movimenti|addebito)\b", re.I),
    "de": re.compile(r"\b(konto|gebühr|vermögen|datum|betrag)\b", re.I),
    "fr": re.compile(r"\b(compte|frais|relevé|montant)\b", re.I),
}
DATE_DMY = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")
DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
AMOUNT = re.compile(r"^[-−(]?\s*(?:CHF|EUR|USD)?\s*\d{1,3}(?:['’ ,.]\d{3})*(?:[.,]\d{1,2})?\)?-?$")
PERCENT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def map_fee_label(text: str) -> str | None:
    for code, pat in FEE_LABELS:
        if pat.search(text):
            return code
    return None


_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            "january januar gennaio janvier jan",
            "february februar febbraio février feb",
            "march märz marzo mars mar",
            "april aprile avril apr",
            "may mai maggio",
            "june juni giugno juin jun",
            "july juli luglio juillet jul",
            "august agosto août aug",
            "september settembre septembre sep sept",
            "october oktober ottobre octobre oct okt",
            "november novembre nov",
            "december dezember dicembre décembre dec dez",
        ],
        start=1,
    )
    for m in names.split()
}
DATE_WORDS = re.compile(r"\b(?:(\d{1,2})\.?\s+)?([a-zäéû]{3,9})\.?\s+(\d{4})\b", re.I)


def find_dates(text: str) -> list[str]:
    """ISO dates found in text: 30.09.2026, 30/09/2026 (day first), 2026-09-30, 3 September 2026,
    1. Januar 2025, and month-year forms such as June 2025 (taken as the first of the month)."""
    out = [f"{y}-{m}-{d}" for d, m, y in DATE_DMY.findall(text)]
    out += [f"{y}-{m}-{d}" for y, m, d in DATE_ISO.findall(text)]
    out += [f"{y}-{int(m):02d}-{int(d):02d}" for d, m, y in DATE_SLASH.findall(text) if int(m) <= 12]
    if not out:
        for d, mon, y in DATE_WORDS.findall(text):
            if mon.lower() in _MONTHS:
                out.append(f"{y}-{_MONTHS[mon.lower()]:02d}-{int(d or 1):02d}")
    return out
