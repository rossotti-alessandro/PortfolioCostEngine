"""Render SYNTHETIC portfolio statements in six bank layout archetypes, with a gold file per statement.

Banks do not publish client statements and real ones are client data, so each statement is a look-alike
of a layout archetype (Swiss private bank in English, cantonal bank in German, Ticino bank in Italian,
Romandy bank in French, Italian bank in EUR, US-style online broker in USD) under a fictitious bank name
that says "(Synthetic)". Holdings are real public ISINs (``universe``); the client, the bank, the
identifiers and the prices are invented. Every page carries a SYNTHETIC watermark and footer.

The planted personal data (name, address, IBAN, portfolio number, phone, email, AHV number) is fake but
well formed (valid IBAN and AHV check digits), so the PII detector is tested on the same pages the
extractor reads.
"""

# ruff: noqa: S311  (seeded test-data generator, not cryptography)
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from stdnum import ean, iban

from .universe import BONDS, STOCKS, Instrument, funds

W, H = A4
CENT = Decimal("0.01")
FX_TO_CHF = {"CHF": Decimal("1"), "USD": Decimal("0.8850"), "EUR": Decimal("0.9350")}
VALUATION = "30.09.2026"
PERIOD = ("01.01.2026", "30.09.2026")


@dataclass(frozen=True)
class Layout:
    key: str
    bank: str
    city: str
    lang: str
    ccy: str
    numfmt: str  # ch | fr | it | us
    title: str
    cols: tuple[str, str, str, str, str, str]  # name, isin, qty, price, ccy, value
    sections: dict[str, str]
    cash_label: str
    total_label: str
    fee_heading: str
    fee_labels: dict[str, str]
    pii_labels: dict[str, str]
    isin_below: bool = False  # broker style: ISIN printed under the name
    domain: str = "example.ch"
    phone_prefix: str = "+41 91"
    iban_country: str = "CH"


LAYOUTS = [
    Layout(
        "ch_private_en", "Banca Lemano (Synthetic) SA", "Via Nassa 1, 6900 Lugano", "en", "CHF", "ch",
        f"Statement of assets as of {VALUATION}",
        ("Description", "ISIN", "Quantity", "Price", "Ccy", "Market value CHF"),
        {"EQUITY": "Equities", "BOND": "Bonds", "FUND": "Investment funds and ETFs", "CASH": "Liquidity"},
        "Current account CHF", "Total assets",
        f"Fees and commissions charged {PERIOD[0]} - {PERIOD[1]}",
        {
            "MGMT_DISCRETIONARY": "Portfolio management fee", "CUSTODY_FEE": "Custody fees",
            "BROKERAGE": "Brokerage commissions", "FX_COMMISSION": "Foreign exchange commission",
            "STAMP_DUTY_CH": "Swiss federal stamp duty", "VAT_ON_FEES": "VAT 8.1% on fees",
        },
        {"client": "Client", "portfolio": "Portfolio no.", "iban": "IBAN", "advisor": "Relationship manager"},
        domain="banca-lemano.example",
    ),
    Layout(
        "ch_cantonal_de", "Kantonalbank Alpenrhein (Synthetic)", "Bahnhofstrasse 12, 9001 St. Gallen", "de",
        "CHF", "ch", f"Vermögensausweis per {VALUATION}",
        ("Bezeichnung", "ISIN", "Anzahl/Nominal", "Kurs", "Whg", "Kurswert CHF"),
        {"EQUITY": "Aktien", "BOND": "Obligationen", "FUND": "Anlagefonds und ETF", "CASH": "Liquidität"},
        "Privatkonto CHF", "Total Vermögen",
        f"Belastete Gebühren und Kommissionen {PERIOD[0]} - {PERIOD[1]}",
        {
            "CUSTODY_FEE": "Depotgebühren", "ACCOUNT_FEE": "Kontoführungsgebühr", "BROKERAGE": "Courtage",
            "THIRD_PARTY_TRADING": "Fremde Spesen", "STAMP_DUTY_CH": "Eidg. Umsatzabgabe",
            "VAT_ON_FEES": "MWST 8.1%",
        },
        {"client": "Kunde", "portfolio": "Depot-Nr.", "iban": "IBAN", "advisor": "Ihr Berater"},
        domain="kb-alpenrhein.example", phone_prefix="+41 71",
    ),
    Layout(
        "ch_ticino_it", "Banca Verbano (Synthetic) SA", "Piazza Grande 5, 6600 Locarno", "it", "CHF", "ch",
        f"Estratto patrimoniale al {VALUATION}",
        ("Descrizione", "ISIN", "Quantità", "Corso", "Div.", "Controvalore CHF"),
        {"EQUITY": "Azioni", "BOND": "Obbligazioni", "FUND": "Fondi d'investimento ed ETF", "CASH": "Liquidità"},  # noqa: E501
        "Conto corrente CHF", "Totale patrimonio",
        f"Commissioni e spese addebitate {PERIOD[0]} - {PERIOD[1]}",
        {
            "ADVISORY_FEE": "Commissione di consulenza", "CUSTODY_FEE": "Diritti di custodia",
            "BROKERAGE": "Commissioni di intermediazione", "FX_COMMISSION": "Commissione di cambio",
            "STAMP_DUTY_CH": "Tassa di bollo federale", "VAT_ON_FEES": "IVA 8.1%",
        },
        {"client": "Cliente", "portfolio": "Relazione n.", "iban": "IBAN", "advisor": "Consulente"},
        domain="banca-verbano.example",
    ),
    Layout(
        "ch_romand_fr", "Banque du Salève (Synthetic) SA", "Rue du Rhône 40, 1204 Genève", "fr", "CHF", "fr",
        f"Relevé de fortune au {VALUATION}",
        ("Désignation", "ISIN", "Quantité", "Cours", "Monnaie", "Valeur CHF"),
        {"EQUITY": "Actions", "BOND": "Obligations", "FUND": "Fonds de placement et ETF", "CASH": "Liquidités"},  # noqa: E501
        "Compte courant CHF", "Total de la fortune",
        f"Frais et commissions débités {PERIOD[0]} - {PERIOD[1]}",
        {
            "MGMT_DISCRETIONARY": "Commission de gestion", "CUSTODY_FEE": "Droits de garde",
            "BROKERAGE": "Courtages", "FX_COMMISSION": "Commission de change",
            "STAMP_DUTY_CH": "Droit de timbre fédéral", "VAT_ON_FEES": "TVA 8.1%",
        },
        {"client": "Client", "portfolio": "Portefeuille n°", "iban": "IBAN", "advisor": "Votre conseiller"},
        domain="banque-saleve.example", phone_prefix="+41 22",
    ),
    Layout(
        "it_bank_eur", "Banca Padana (Synthetic) S.p.A.", "Corso Zanardelli 8, 25121 Brescia", "it", "EUR", "it",  # noqa: E501
        "Rendiconto titoli al 30/09/2026",
        ("Titolo", "Codice ISIN", "Quantità", "Prezzo", "Divisa", "Controvalore EUR"),
        {"EQUITY": "Azioni", "BOND": "Titoli di Stato e obbligazioni", "FUND": "Fondi comuni ed ETF",
         "CASH": "Liquidità"},
        "Conto corrente EUR", "Totale controvalore",
        f"Commissioni e spese {PERIOD[0]} - {PERIOD[1]}",
        {
            "CUSTODY_FEE": "Spese di custodia e amministrazione titoli", "ACCOUNT_FEE": "Spese tenuta conto",
            "BROKERAGE": "Commissioni di negoziazione", "ADVISORY_FEE": "Commissione di consulenza",
        },
        {"client": "Intestatario", "portfolio": "Dossier titoli n.", "iban": "IBAN", "advisor": "Gestore"},
        domain="banca-padana.example", phone_prefix="+39 030", iban_country="IT",
    ),
    Layout(
        "broker_en_usd", "Harbor Online Brokers (Synthetic) LLC", "100 Pine Street, San Francisco, CA",
        "en", "USD", "us", "Account statement - holdings as of 09/30/2026",
        ("Description", "ISIN", "Quantity", "Price", "Ccy", "Market value USD"),
        {"EQUITY": "Stocks", "BOND": "Fixed income", "FUND": "ETFs and mutual funds", "CASH": "Cash"},
        "Cash balance USD", "Total account value",
        "Fees and commissions",
        {"BROKERAGE": "Commissions", "THIRD_PARTY_TRADING": "Exchange and regulatory fees",
         "FX_COMMISSION": "Currency conversion fee", "ACCOUNT_FEE": "Account maintenance fee"},
        {"client": "Account holder", "portfolio": "Account number", "iban": "IBAN", "advisor": "Support"},
        isin_below=True, domain="harbor-brokers.example", phone_prefix="+41 44",
    ),
]  # fmt: skip

FIRST = ["Luca", "Giulia", "Marco", "Chiara", "Andrea", "Sara", "Thomas", "Anna", "Daniel", "Laura",
         "Pierre", "Claire", "Nicolas", "Sophie", "Matteo", "Elena", "Stefan", "Monika", "David", "Martina"]  # fmt: skip  # noqa: E501
LAST = ["Bernasconi", "Keller", "Fontana", "Meier", "Rochat", "Ferrari", "Brunner", "Galli", "Favre",
        "Huber", "Colombo", "Moser", "Bianchi", "Steiner", "Dubois", "Rossi", "Gerber", "Ricci"]  # fmt: skip
STREETS = [
    "Via Cantonale",
    "Hauptstrasse",
    "Avenue de la Gare",
    "Via Roma",
    "Seestrasse",
    "Chemin des Vignes",
]
TOWNS = ["6900 Lugano", "8001 Zürich", "1003 Lausanne", "6500 Bellinzona", "3011 Bern", "20121 Milano"]


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(x: Decimal, numfmt: str, places: int = 2) -> str:
    s = f"{x:,.{places}f}"
    if numfmt == "ch":
        return s.replace(",", "'")
    if numfmt == "fr":
        return s.replace(",", " ")
    if numfmt == "it":
        return s.replace(",", "_").replace(".", ",").replace("_", ".")
    return s


@dataclass
class Holding:
    inst: Instrument
    quantity: Decimal
    value: Decimal  # in the statement currency


@dataclass
class Gold:
    file: str
    layout: str
    lang: str
    currency: str
    positions: list[dict] = field(default_factory=list)  # isin, name, value, page, kind
    cash: list[dict] = field(default_factory=list)
    total: str = ""
    fees: list[dict] = field(default_factory=list)  # code, label, value, page
    pii: list[dict] = field(default_factory=list)  # kind, text, page
    fx: dict[str, str] = field(default_factory=dict)


def _fake_iban(rng: random.Random, country: str) -> str:
    if country == "IT":
        body = (
            "X"
            + "".join(rng.choice("0123456789") for _ in range(10))
            + "".join(rng.choice("0123456789") for _ in range(12))
        )
    else:
        body = "".join(rng.choice("0123456789") for _ in range(17))
    raw = country + "00" + body
    return iban.format(country + iban.calc_check_digits(raw) + body)


def _fake_ahv(rng: random.Random) -> str:
    d = "756" + "".join(rng.choice("0123456789") for _ in range(9))
    d += ean.calc_check_digit(d)
    return f"{d[:3]}.{d[3:7]}.{d[7:11]}.{d[11:]}"


def _value(inst: Instrument, qty: Decimal, ccy: str) -> Decimal:
    local = qty * inst.price / (100 if inst.kind == "BOND" else 1)
    return q(local * FX_TO_CHF[inst.currency] / FX_TO_CHF[ccy])


def _portfolio(rng: random.Random, lay: Layout) -> list[Holding]:
    home = {"CHF": "CH", "EUR": ("IT", "DE", "FR", "NL"), "USD": "US"}[lay.ccy]
    stocks = [s for s in STOCKS if s.isin.startswith(home)] + rng.sample(STOCKS, 4)
    bonds = [b for b in BONDS if b.currency == lay.ccy] or BONDS
    fs = funds()
    picks = rng.sample(sorted(set(stocks), key=lambda i: i.isin), min(len(set(stocks)), rng.randint(3, 8)))
    picks += rng.sample(bonds, min(len(bonds), rng.randint(1, 3)))
    picks += rng.sample(fs, rng.randint(3, 9))
    out = []
    for inst in picks:
        target = Decimal(rng.choice([25, 40, 60, 80, 120, 150, 200, 300])) * 1000
        if inst.kind == "BOND":
            nominal = target / FX_TO_CHF[inst.currency] * FX_TO_CHF[lay.ccy] * 100 / inst.price
            qty = Decimal(max(1, round(nominal / 10000)) * 10000)  # nominal in round 10'000s
        else:
            local = target / FX_TO_CHF[inst.currency] * FX_TO_CHF[lay.ccy]
            qty = Decimal(max(1, int(local / inst.price)))
        out.append(Holding(inst, qty, _value(inst, qty, lay.ccy)))
    return out


def _fees(rng: random.Random, lay: Layout, aum: Decimal) -> list[tuple[str, str, Decimal]]:
    rates = {
        "MGMT_DISCRETIONARY": "0.0075", "ADVISORY_FEE": "0.0045", "CUSTODY_FEE": "0.0015",
        "BROKERAGE": "0.0022", "FX_COMMISSION": "0.0004", "STAMP_DUTY_CH": "0.0003",
        "THIRD_PARTY_TRADING": "0.0001", "ACCOUNT_FEE": None, "VAT_ON_FEES": None,
    }  # fmt: skip
    out = []
    for code, label in lay.fee_labels.items():
        if code == "ACCOUNT_FEE":
            amt = Decimal(rng.choice(["60.00", "90.00", "120.00", "36.00"]))
        elif code == "VAT_ON_FEES":
            base = sum(
                (a for c, _, a in out if c in ("MGMT_DISCRETIONARY", "ADVISORY_FEE", "CUSTODY_FEE")),
                Decimal(0),
            )
            amt = q(base * Decimal("0.081"))
        else:
            r = Decimal(rates[code]) * Decimal(rng.randint(70, 130)) / 100
            amt = q(aum * r * Decimal(9) / 12)
        out.append((code, label, amt))
    return out


class _Pdf:
    """Minimal page writer with the SYNTHETIC watermark and footer on every page."""

    def __init__(self, path: Path, lay: Layout):
        self.c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
        self.c.setTitle(f"SYNTHETIC statement - {lay.bank}")
        self.c.setSubject("SYNTHETIC TEST DOCUMENT - fictitious bank and client, real public ISINs")
        self.lay = lay
        self.page = 0
        self.y = 0.0

    def new_page(self) -> None:
        if self.page:
            self.c.showPage()
        self.page += 1
        c, lay = self.c, self.lay
        c.saveState()
        c.setFillColor(Color(0.8, 0.2, 0.2, alpha=0.08))
        c.setFont("Helvetica-Bold", 60)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "SYNTHETIC")
        c.restoreState()
        c.setFillColor(HexColor("#123B5D"))
        c.rect(0, H - 6, W, 6, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, H - 38, lay.bank)
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#555555"))
        c.drawString(40, H - 50, lay.city)
        c.drawRightString(W - 40, H - 38, f"{self.page}")
        c.setFont("Helvetica", 6.5)
        c.drawString(40, 22, "SYNTHETIC TEST DOCUMENT - fictitious bank and client. ISINs are real public "
                     "instruments; prices are illustrative, not market data.")  # fmt: skip
        c.setFillColor(HexColor("#000000"))
        self.y = H - 75

    def text(self, x: float, s: str, size: float = 8.5, bold: bool = False, right: bool = False) -> None:
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        (self.c.drawRightString if right else self.c.drawString)(x, self.y, s)


COLS_X = (40, 245, 360, 425, 470, 555)  # name, isin, qty(right), price(right), ccy, value(right)


def render(path: Path, lay: Layout, seed: int) -> Gold:
    rng = random.Random(seed)
    holdings = _portfolio(rng, lay)
    cash = q(Decimal(rng.randint(5, 180)) * 1000 + Decimal(rng.randint(0, 99)) / 100)
    total = sum((h.value for h in holdings), Decimal(0)) + cash
    gold = Gold(path.name, lay.key, lay.lang, lay.ccy, total=str(total))
    for k in ("USD", "EUR", "CHF"):
        if k != lay.ccy:
            gold.fx[f"{k}/{lay.ccy}"] = str((FX_TO_CHF[k] / FX_TO_CHF[lay.ccy]).quantize(Decimal("0.0001")))
    name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    street = f"{rng.choice(STREETS)} {rng.randint(1, 120)}"
    town = rng.choice(TOWNS)
    portfolio_no = f"{rng.randint(100, 999)}-{rng.randint(100000, 999999)}.{rng.randint(1, 9):02d}"
    acct_iban = _fake_iban(rng, lay.iban_country)
    advisor = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
    phone = f"{lay.phone_prefix} {rng.randint(100, 999)} {rng.randint(10, 99)} {rng.randint(10, 99)}"
    email = f"{advisor.split()[0][0].lower()}.{advisor.split()[1].lower()}@{lay.domain}"
    ahv = _fake_ahv(rng) if lay.lang in ("de", "fr") else None

    pdf = _Pdf(path, lay)
    pdf.new_page()
    c = pdf.c
    pl = lay.pii_labels
    for line, kind in ((name, "name"), (street, "address"), (town, "address")):
        pdf.text(330, line, 9)
        gold.pii.append({"kind": kind, "text": line, "page": 1})
        pdf.y -= 12
    pdf.y -= 8
    rows = [
        (f"{pl['client']}: {name}", None),
        (f"{pl['portfolio']}: {portfolio_no}", ("account", portfolio_no)),
        (f"{pl['iban']}: {acct_iban}", ("iban", acct_iban)),
        (f"{pl['advisor']}: {advisor}, Tel. {phone}, {email}", None),
    ]
    if ahv:
        rows.append((f"AHV/AVS: {ahv}", ("ahv", ahv)))
    for s, pii in rows:
        pdf.text(40, s, 8.5)
        pdf.y -= 12
        if pii:
            gold.pii.append({"kind": pii[0], "text": pii[1], "page": 1})
    gold.pii += [
        {"kind": "name", "text": advisor, "page": 1},
        {"kind": "phone", "text": phone, "page": 1},
        {"kind": "email", "text": email, "page": 1},
    ]
    pdf.y -= 10
    pdf.text(40, lay.title, 14, bold=True)
    pdf.y -= 16
    ref = {"en": "Reference currency", "de": "Referenzwährung", "it": "Valuta di riferimento",
           "fr": "Monnaie de référence"}[lay.lang]  # fmt: skip
    fx_s = "   ".join(f"{k} {fmt(Decimal(v), lay.numfmt, 4)}" for k, v in gold.fx.items())
    pdf.text(40, f"{ref}: {lay.ccy}     {fx_s}", 8)
    pdf.y -= 22

    def table_header() -> None:
        c.setFillColor(HexColor("#E8EDF2"))
        c.rect(36, pdf.y - 4, W - 72, 14, fill=1, stroke=0)
        c.setFillColor(HexColor("#000000"))
        name_c, isin_c, qty_c, price_c, ccy_c, val_c = lay.cols
        if lay.isin_below:
            pdf.text(COLS_X[0], f"{name_c} / {isin_c}", 8, bold=True)
        else:
            pdf.text(COLS_X[0], name_c, 8, bold=True)
            pdf.text(COLS_X[1], isin_c, 8, bold=True)
        pdf.text(COLS_X[2], qty_c, 8, bold=True, right=True)
        pdf.text(COLS_X[3], price_c, 8, bold=True, right=True)
        pdf.text(COLS_X[4], ccy_c, 8, bold=True)
        pdf.text(COLS_X[5], val_c, 8, bold=True, right=True)
        pdf.y -= 18

    def need(h: float) -> None:
        if pdf.y - h < 60:
            pdf.new_page()
            pdf.y -= 10
            table_header()

    table_header()
    order = ["EQUITY", "BOND", "FUND"]
    for kind in order:
        group = [h for h in holdings if (h.inst.kind if h.inst.kind != "ETF" else "FUND") == kind]
        if not group:
            continue
        need(40)
        pdf.text(COLS_X[0], lay.sections[kind], 9, bold=True)
        pdf.y -= 14
        for h in group:
            need(26 if lay.isin_below else 14)
            nm = h.inst.name if len(h.inst.name) <= 44 else h.inst.name[:43] + "."
            pdf.text(COLS_X[0], nm, 7.8)
            if not lay.isin_below:
                pdf.text(COLS_X[1], h.inst.isin, 7.8)
            places = 0 if h.quantity == h.quantity.to_integral() else 3
            pdf.text(COLS_X[2], fmt(h.quantity, lay.numfmt, places), 7.8, right=True)
            pdf.text(COLS_X[3], fmt(h.inst.price, lay.numfmt), 7.8, right=True)
            pdf.text(COLS_X[4], h.inst.currency, 7.8)
            pdf.text(COLS_X[5], fmt(h.value, lay.numfmt), 7.8, right=True)
            gold.positions.append(
                {
                    "isin": h.inst.isin,
                    "name": h.inst.name,
                    "kind": h.inst.kind,
                    "quantity": str(h.quantity),
                    "value": str(h.value),
                    "page": pdf.page,
                }
            )
            if lay.isin_below:
                pdf.y -= 10
                pdf.text(COLS_X[0] + 8, f"ISIN {h.inst.isin}", 7)
            pdf.y -= 13
        pdf.y -= 4
    need(50)
    pdf.text(COLS_X[0], lay.sections["CASH"], 9, bold=True)
    pdf.y -= 14
    pdf.text(COLS_X[0], lay.cash_label, 7.8)
    pdf.text(COLS_X[5], fmt(cash, lay.numfmt), 7.8, right=True)
    gold.cash.append({"label": lay.cash_label, "value": str(cash), "page": pdf.page})
    pdf.y -= 18
    c.line(36, pdf.y + 10, W - 36, pdf.y + 10)
    pdf.text(COLS_X[0], lay.total_label, 9, bold=True)
    pdf.text(COLS_X[5], fmt(total, lay.numfmt), 9, bold=True, right=True)

    pdf.new_page()
    pdf.y -= 10
    pdf.text(40, lay.fee_heading, 12, bold=True)
    pdf.y -= 24
    fee_total = Decimal(0)
    for code, label, amt in _fees(rng, lay, total):
        pdf.text(40, label, 9)
        pdf.text(W - 60, fmt(amt, lay.numfmt), 9, right=True)
        gold.fees.append({"code": code, "label": label, "value": str(amt), "page": pdf.page})
        fee_total += amt
        pdf.y -= 16
    c.line(36, pdf.y + 10, W - 36, pdf.y + 10)
    pdf.text(40, {"en": "Total", "de": "Total", "it": "Totale", "fr": "Total"}[lay.lang], 9, bold=True)
    pdf.text(W - 60, fmt(fee_total, lay.numfmt), 9, bold=True, right=True)
    c.save()
    return gold


def build(out: Path, n: int, seed: int = 2026) -> list[Gold]:
    """``n`` statements cycling through the layouts; writes ``<file>.pdf`` and ``gold.json`` into ``out``."""
    out.mkdir(parents=True, exist_ok=True)
    golds = []
    for i in range(n):
        lay = LAYOUTS[i % len(LAYOUTS)]
        golds.append(render(out / f"synthetic-{i + 1:02d}-{lay.key}.pdf", lay, seed + i))
    (out / "gold.json").write_text(json.dumps([asdict(g) for g in golds], indent=1), encoding="utf-8")
    return golds
