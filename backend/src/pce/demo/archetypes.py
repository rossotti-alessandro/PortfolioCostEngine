"""Second SYNTHETIC prospect (P-2077) built from layout archetypes of other institution types.

Ale asked for test documents that look like the statements an analyst really receives
(an Italian bank, a US-style online broker). Banks do not publish client statements and
real ones are client data, so these are look-alikes of the *layout archetype* with
fictitious institution names: never a real brand, so no file can pass as a genuine
statement. What each archetype exercises:

- Banca Delta (Synthetic) S.p.A., Milano: Italian language, EUR with comma decimals
  ("1.234,56"), "Controvalore" column, an MiFID II ex-post "costi e oneri" report with
  inducements, an Italian-language KID, and an EUR/CHF rate printed on the statement.
- Northgate Brokers (Synthetic) LLC: one English "activity statement" carrying both open
  positions and a fees section, USD amounts with comma thousands, a USD/CHF rate, and a
  real public instrument (IE00B4L5Y983) whose KID was not supplied, so its product cost
  must stay "not determined".

Run: ``python -m pce.demo.archetypes <out_dir>``. Output is deterministic.
"""

from __future__ import annotations

import sys
from decimal import Decimal as Dec
from pathlib import Path

from reportlab.lib.pagesizes import A4

from .generate import Doc

W, _H = A4
PROSPECT_CODE = "P-2077"
PROSPECT_LABEL = "Prospect P-2077 (synthetic, multi-custodian)"
CLIENT_DOMICILE = "CH"
VALUATION = "30.09.2026"

DELTA = "Banca Delta (Synthetic) S.p.A."
DELTA_CITY = "Milano, Italia"
EUR_CHF = Dec("0.9350")
DELTA_POSITIONS = [  # (name, isin, quantity, price, value EUR)
    (
        "Fondo Bilanciato Italia (Synthetic) classe A",
        "ZZFBILIT0018",
        Dec("120000"),
        Dec("5.00"),
        Dec("600000.00"),
    ),
    (
        "Italy Government Bond 2.5% 2030 (Synthetic)",
        "ZZITGOVB0306",
        Dec("400000"),
        Dec("100.00"),
        Dec("400000.00"),
    ),
]
DELTA_CASH = Dec("50000.00")
DELTA_TOTAL = Dec("1050000.00")
DELTA_COSTS = [  # (label, value EUR) as printed in the ex-post report
    ("Commissioni di gestione patrimoniale", Dec("9600.00")),
    ("Diritti di custodia titoli", Dec("1200.00")),
    ("Commissioni di intermediazione", Dec("2150.00")),
    ("Spese tenuta conto", Dec("240.00")),
]
DELTA_PRODUCT_COSTS = Dec("11500.00")
DELTA_INDUCEMENTS = Dec("4500.00")
DELTA_KID = {  # Italian-language KID of the balanced fund
    "isin": "ZZFBILIT0018",
    "name": "Fondo Bilanciato Italia (Synthetic) classe A",
    "ongoing": Dec("1.85"),
    "mgmt": Dec("1.50"),
    "transaction": Dec("0.12"),
    "entry_max": Dec("2.00"),
}

NORTHGATE = "Northgate Brokers (Synthetic) LLC"
NORTHGATE_CITY = "New York, United States"
USD_CHF = Dec("0.8000")
NORTHGATE_POSITIONS = [  # (name, isin, quantity, close price, value USD)
    (
        "iShares Core MSCI World UCITS ETF USD (Acc)",
        "IE00B4L5Y983",
        Dec("7000"),
        Dec("100.00"),
        Dec("700000.00"),
    ),
    ("Global Tech Equity Inc. (Synthetic)", "ZZGLTECH0011", Dec("1500"), Dec("200.00"), Dec("300000.00")),
]
NORTHGATE_CASH = Dec("50000.00")
NORTHGATE_TOTAL = Dec("1050000.00")
NORTHGATE_FEES = [  # (label, value USD)
    ("Commissions", Dec("1850.00")),
    ("Market data subscriptions", Dec("360.00")),
    ("FX conversion fees", Dec("140.00")),
]


def it_num(x: Dec) -> str:
    """Italian formatting 1.234.567,89"""
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def us_num(x: Dec) -> str:
    return f"{x:,.2f}"


def delta_statement(out: Path) -> None:
    d = Doc(out / "delta_situazione_patrimoniale_2026-09-30.pdf", "Situazione patrimoniale")
    d.header(
        DELTA,
        DELTA_CITY,
        "Situazione patrimoniale dossier titoli",
        f"Data di valutazione {VALUATION} · Valori in EUR",
    )
    d.kv("Cliente", PROSPECT_LABEL)
    d.kv("Dossier", "Dossier titoli 77-0412 · Gestione patrimoniale")
    d.kv("Data di valutazione", VALUATION)
    d.section("Posizioni")
    d.row(
        [
            (50, "Titolo", "l"),
            (260, "ISIN", "l"),
            (370, "Quantità", "r"),
            (440, "Prezzo", "r"),
            (W - 50, "Controvalore EUR", "r"),
        ],
        bold=True,
        size=8.5,
    )
    for name, isin, qty, price, val in DELTA_POSITIONS:
        d.row(
            [
                (50, name, "l"),
                (260, isin, "l"),
                (370, it_num(qty).replace(",00", ""), "r"),
                (440, it_num(price), "r"),
                (W - 50, it_num(val), "r"),
            ],
            size=8.5,
        )
    d.row([(50, "Conto corrente EUR", "l"), (W - 50, it_num(DELTA_CASH), "r")], size=8.5)
    d.row([(50, "Totale patrimonio", "l"), (W - 50, it_num(DELTA_TOTAL), "r")], bold=True, size=8.5)
    d.y -= 10
    d.para(f"Tasso di cambio EUR/CHF al {VALUATION}: {str(EUR_CHF).replace('.', ',')}")
    d.save()


def delta_cost_report(out: Path) -> None:
    d = Doc(out / "delta_rendiconto_costi_oneri_2025-2026.pdf", "Rendiconto costi e oneri")
    d.header(
        DELTA,
        DELTA_CITY,
        "Rendiconto annuale dei costi e oneri",
        "Periodo dal 01.10.2025 al 30.09.2026 · Informativa ex-post MiFID II · Valori in EUR",
    )
    d.kv("Cliente", PROSPECT_LABEL)
    d.kv("Dossier", "77-0412 · Gestione patrimoniale")
    d.section("Costi dei servizi")
    d.row([(50, "Voce di costo", "l"), (W - 50, "Importo EUR", "r")], bold=True)
    for label, amt in DELTA_COSTS:
        d.row([(50, label, "l"), (W - 50, it_num(amt), "r")])
    d.row(
        [
            (50, "Totale costi dei servizi", "l"),
            (W - 50, it_num(sum((a for _l, a in DELTA_COSTS), Dec(0))), "r"),
        ],
        bold=True,
    )
    d.section("Costi di prodotto (stima)")
    d.row(
        [
            (50, "Costi correnti e di transazione degli strumenti finanziari", "l"),
            (W - 50, it_num(DELTA_PRODUCT_COSTS), "r"),
        ]
    )
    d.section("Incentivi")
    d.row([(50, "Incentivi percepiti dalla banca", "l"), (W - 50, it_num(DELTA_INDUCEMENTS), "r")])
    d.para(
        "Gli incentivi sono pagati dalle società prodotto e sono inclusi nei costi di prodotto "
        "indicati sopra."
    )
    d.save()


def delta_kid(out: Path) -> None:
    k = DELTA_KID
    d = Doc(out / f"kid_{k['isin']}_it.pdf", "Documento contenente le informazioni chiave")
    d.header(
        "Synthetic SGR S.p.A.",
        "Gestore sintetico",
        "Documento contenente le informazioni chiave",
        f"{k['name']} · ISIN {k['isin']} · Data di realizzazione 10.01.2026",
    )
    d.kv("Prodotto", k["name"])
    d.kv("ISIN", k["isin"])
    d.section("Quali sono i costi?")
    d.row([(50, "Costi una tantum di ingresso o di uscita", "l")], bold=True)
    d.row([(50, "Costi di ingresso (massimo)", "l"), (W - 50, f"fino a {it_num(k['entry_max'])}%", "r")])
    d.row([(50, "Costi di uscita", "l"), (W - 50, "0,00%", "r")])
    d.row([(50, "Costi correnti registrati ogni anno", "l")], bold=True)
    d.row(
        [
            (50, "Spese correnti di gestione e altri costi amministrativi", "l"),
            (W - 50, f"{it_num(k['ongoing'])}%", "r"),
        ]
    )
    d.row([(70, "di cui commissione di gestione", "l"), (W - 50, f"{it_num(k['mgmt'])}%", "r")])
    d.row([(50, "Costi di transazione", "l"), (W - 50, f"{it_num(k['transaction'])}%", "r")])
    d.row([(50, "Commissioni di performance", "l"), (W - 50, "0,00%", "r")])
    d.save()


def northgate_activity(out: Path) -> None:
    d = Doc(out / "northgate_activity_statement_2025-2026.pdf", "Activity statement")
    d.header(
        NORTHGATE,
        NORTHGATE_CITY,
        "Activity Statement",
        "Period 2025-10-01 to 2026-09-30 · Base currency USD",
    )
    d.kv("Account", "U-0099213 (Synthetic) · Individual")
    d.kv("Valuation date", "2026-09-30")
    d.section("Open Positions")
    d.row(
        [
            (50, "Description", "l"),
            (280, "ISIN", "l"),
            (370, "Quantity", "r"),
            (440, "Close Price", "r"),
            (W - 50, "Value USD", "r"),
        ],
        bold=True,
        size=8.5,
    )
    for name, isin, qty, price, val in NORTHGATE_POSITIONS:
        d.row(
            [
                (50, name, "l"),
                (280, isin, "l"),
                (370, us_num(qty)[:-3], "r"),
                (440, us_num(price), "r"),
                (W - 50, us_num(val), "r"),
            ],
            size=8.5,
        )
    d.row([(50, "Cash USD", "l"), (W - 50, us_num(NORTHGATE_CASH), "r")], size=8.5)
    d.row([(50, "Total Net Asset Value", "l"), (W - 50, us_num(NORTHGATE_TOTAL), "r")], bold=True, size=8.5)
    d.section("Fees and Commissions")
    d.row([(50, "Item", "l"), (W - 50, "Amount USD", "r")], bold=True)
    for label, amt in NORTHGATE_FEES:
        d.row([(50, label, "l"), (W - 50, us_num(amt), "r")])
    d.row(
        [(50, "Total fees", "l"), (W - 50, us_num(sum((a for _l, a in NORTHGATE_FEES), Dec(0))), "r")],
        bold=True,
    )
    d.y -= 6
    d.para(f"FX rate USD/CHF 2026-09-30: {USD_CHF}")
    d.save()


def generate(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    delta_statement(out)
    delta_cost_report(out)
    delta_kid(out)
    northgate_activity(out)
    return sorted(p for p in out.iterdir() if p.is_file())


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/synthetic/prospect_p2077")
    for p in generate(target):
        print(p)
