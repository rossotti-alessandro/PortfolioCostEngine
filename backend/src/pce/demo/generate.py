"""Render the SYNTHETIC demo prospect into bank-style documents.

Run: ``python -m pce.demo.generate <out_dir>``. Output is deterministic.
Every page carries a diagonal "SYNTHETIC – DEMO DATA" watermark; the extractor
ignores rotated text, so the watermark never pollutes extracted facts.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from . import spec as S

NAVY = HexColor("#0B2545")
GREY = HexColor("#5B6573")
LINE = HexColor("#C9CED6")
W, H = A4


def chf(x: Decimal) -> str:
    """Swiss formatting 1'234'567.89"""
    s = f"{x:,.2f}".replace(",", "'")
    return s


def pct(x: Decimal) -> str:
    return f"{x:.2f}%"


class Doc:
    def __init__(self, path: Path, title: str):
        self.c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
        self.c.setTitle(title)
        self.c.setAuthor("PortfolioCostEngine synthetic generator")
        self.c.setSubject("SYNTHETIC DEMO DOCUMENT - not a real bank document")
        self.y = H - 60
        self.page = 1

    def watermark(self):
        c = self.c
        c.saveState()
        c.setFillColor(Color(0.85, 0.2, 0.2, alpha=0.12))
        c.setFont("Helvetica-Bold", 54)
        c.translate(W / 2, H / 2)
        c.rotate(35)
        c.drawCentredString(0, 0, "SYNTHETIC - DEMO DATA")
        c.restoreState()

    def header(self, bank: str, city: str, title: str, subtitle: str = ""):
        c = self.c
        self.watermark()
        c.setFillColor(NAVY)
        c.rect(0, H - 8, W, 8, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, H - 45, bank)
        c.setFont("Helvetica", 9)
        c.setFillColor(GREY)
        c.drawString(50, H - 58, city)
        c.drawRightString(W - 50, H - 45, f"Page {self.page}")
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, H - 95, title)
        c.setFont("Helvetica", 10)
        c.setFillColor(GREY)
        if subtitle:
            c.drawString(50, H - 112, subtitle)
        self.y = H - 140
        self.footer()

    def footer(self):
        c = self.c
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        c.drawString(50, 30, "Synthetic document generated for software demonstration. Not issued by any bank. "
                             "All names, identifiers and amounts are fictitious.")

    def kv(self, k: str, v: str, x2: float = 230):
        c = self.c
        c.setFont("Helvetica", 9.5)
        c.setFillColor(GREY)
        c.drawString(50, self.y, k)
        c.setFillColor(NAVY)
        c.drawString(x2, self.y, v)
        self.y -= 16

    def section(self, title: str):
        self.y -= 8
        c = self.c
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(NAVY)
        c.drawString(50, self.y, title)
        self.y -= 6
        c.setStrokeColor(LINE)
        c.line(50, self.y, W - 50, self.y)
        self.y -= 16

    def row(self, cols: list[tuple[float, str, str]], bold: bool = False, size: float = 9):
        """cols: (x, text, align) with align in l/r"""
        c = self.c
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(NAVY)
        for x, text, align in cols:
            if align == "r":
                c.drawRightString(x, self.y, text)
            else:
                c.drawString(x, self.y, text)
        self.y -= 15

    def para(self, text: str, size: float = 9):
        c = self.c
        c.setFont("Helvetica", size)
        c.setFillColor(GREY)
        words, line = text.split(), ""
        for w in words:
            if c.stringWidth(line + " " + w, "Helvetica", size) > W - 100:
                c.drawString(50, self.y, line.strip())
                self.y -= size + 4
                line = ""
            line += " " + w
        if line.strip():
            c.drawString(50, self.y, line.strip())
            self.y -= size + 4

    def new_page(self):
        self.c.showPage()
        self.page += 1

    def save(self):
        self.c.showPage()
        self.c.save()


def alpha_statement(out: Path):
    d = Doc(out / "alpha_statement_of_assets_2026-09-30.pdf", "Statement of assets")
    d.header(S.ALPHA, S.ALPHA_CITY, "Statement of assets", f"Valuation date {S.VALUATION_DATE} · Reference currency CHF")
    d.kv("Client", S.PROSPECT_LABEL)
    d.kv("Portfolio", "Advisory mandate · Portfolio 4512-01")
    d.kv("Booking centre", "Switzerland")
    d.kv("Valuation date", "30.09.2026")
    d.section("Summary by asset class")
    groups: dict[str, Decimal] = {}
    for p in S.ALPHA_POSITIONS:
        groups[p.asset_class] = groups.get(p.asset_class, Decimal(0)) + p.value_chf
    labels = {"FUND": "Investment funds", "ETF": "Exchange traded funds", "EQUITY": "Equities",
              "STRUCTURED": "Structured products", "CASH": "Liquidity"}
    for k, v in groups.items():
        d.row([(50, labels[k], "l"), (W - 50, f"CHF {chf(v)}", "r")])
    d.row([(50, "Total assets", "l"), (W - 50, f"CHF {chf(S.ALPHA_TOTAL)}", "r")], bold=True)
    d.new_page()
    d.page = 2
    d.header(S.ALPHA, S.ALPHA_CITY, "Positions", "Valuation date 30.09.2026 · Values in CHF")
    d.row([(50, "Description", "l"), (250, "ISIN", "l"), (370, "Quantity", "r"), (440, "Price", "r"),
           (W - 50, "Market value CHF", "r")], bold=True, size=8.5)
    for p in S.ALPHA_POSITIONS:
        if p.isin:
            d.row([(50, p.name, "l"), (250, p.isin, "l"), (370, chf(p.quantity).replace(".00", ""), "r"),
                   (440, chf(p.price), "r"), (W - 50, chf(p.value_chf), "r")], size=8.5)
        else:
            d.row([(50, p.name, "l"), (W - 50, chf(p.value_chf), "r")], size=8.5)
    d.row([(50, "Total assets", "l"), (W - 50, chf(S.ALPHA_TOTAL), "r")], bold=True, size=8.5)
    d.y -= 10
    d.para("Market values are indicative and based on the last available prices. Accrued interest is not included.")
    d.save()


def alpha_cost_report(out: Path):
    d = Doc(out / "alpha_costs_and_charges_2025-2026.pdf", "Costs and charges report")
    d.header(S.ALPHA, S.ALPHA_CITY, "Annual report on costs and charges",
             "Period 01.10.2025 - 30.09.2026 · Ex-post disclosure · Currency CHF")
    d.kv("Client", S.PROSPECT_LABEL)
    d.kv("Portfolio", "4512-01 · Advisory mandate")
    d.kv("Average assets in period", "CHF 3'200'000.00")
    d.section("Service costs charged by the bank")
    d.row([(50, "Cost item", "l"), (W - 50, "Amount CHF", "r")], bold=True)
    for label, _code, amt in S.ALPHA_COST_REPORT:
        d.row([(50, label, "l"), (W - 50, chf(amt), "r")])
    total = sum((a for *_x, a in S.ALPHA_COST_REPORT), Decimal(0))
    d.row([(50, "Total service costs", "l"), (W - 50, chf(total), "r")], bold=True)
    d.section("Third-party product costs (estimate)")
    d.row([(50, "Ongoing and transaction costs of financial instruments", "l"),
           (W - 50, chf(S.ALPHA_REPORTED_PRODUCT_COSTS), "r")])
    d.para("Product costs are not debited from your account. They are included in the price of the instruments "
           "and are estimated by the bank from manufacturer disclosures.")
    d.section("Inducements")
    d.row([(50, "Retrocessions received by the bank", "l"), (W - 50, chf(S.ALPHA_RETROCESSIONS), "r")])
    d.para("Retrocessions are paid by product providers out of the product costs shown above. They are not an "
           "additional charge to the client.")
    d.save()


def alpha_tariff(out: Path):
    t = S.ALPHA_TARIFF
    d = Doc(out / "alpha_price_schedule_2026.pdf", "Price schedule")
    d.header(S.ALPHA, S.ALPHA_CITY, "Price schedule for private clients", "Valid from 01.01.2026 · Switzerland")
    d.kv("Issuing entity", f"{S.ALPHA}, Lugano (Switzerland)")
    d.kv("Applies to", "Accounts booked in Switzerland")
    d.section("Advisory and custody")
    d.row([(50, "Advisory mandate fee p.a. on total assets", "l"), (W - 50, pct(t["advisory_pct"]), "r")])
    d.row([(50, "Custody fee p.a. on securities (cash excluded)", "l"), (W - 50, pct(t["custody_pct"]), "r")])
    d.row([(50, "Minimum custody fee p.a.", "l"), (W - 50, f"CHF {chf(t['custody_min'])}", "r")])
    d.section("Transactions")
    d.row([(50, "Brokerage on stock exchange trades", "l"), (W - 50, pct(t["brokerage_pct"]), "r")])
    d.row([(50, "Minimum per trade", "l"), (W - 50, f"CHF {chf(t['brokerage_min'])}", "r")])
    d.row([(50, "Transfer of securities to another bank, per position", "l"),
           (W - 50, f"CHF {chf(t['transfer_out_per_position'])}", "r")])
    d.para("Swiss VAT at the applicable rate is added to custody fees. Third-party costs and taxes are charged "
           "separately.")
    d.save()


def beta_lu_tariff(out: Path):
    t = S.BETA_LU_TARIFF
    d = Doc(out / "beta_europe_price_schedule_2026.pdf", "Schedule of prices")
    d.header(S.BETA_LU, S.BETA_LU_CITY, "Schedule of prices - banking and custody", "Valid from 01.01.2026 · Luxembourg")
    d.kv("Issuing entity", f"{S.BETA_LU}, Luxembourg")
    d.kv("Applies to", "Accounts booked in Luxembourg")
    d.section("Custody")
    d.row([(50, "Custody fee p.a. on securities", "l"), (W - 50, pct(t["custody_pct"]), "r")])
    d.row([(50, "Minimum custody fee per quarter", "l"), (W - 50, f"EUR {chf(t['custody_min_quarter'])}", "r")])
    d.save()


def kid(out: Path, isin: str, k: dict):
    d = Doc(out / f"kid_{isin}.pdf", "Key Information Document")
    d.header(k["manufacturer"], "Synthetic manufacturer", "Key Information Document",
             f"{k['name']} · ISIN {isin} · Date of production {k['date']}")
    d.para("Purpose: This document provides you with key information about this investment product. "
           "It is not marketing material.")
    d.kv("Product", k["name"])
    d.kv("ISIN", isin)
    d.kv("Manufacturer", k["manufacturer"])
    d.section("What are the costs?")
    d.para("Costs over time - example investment 10'000 (illustrative only, not the costs you actually pay):")
    total_y1 = (Decimal(10000) * (k["ongoing"] + k["transaction"]) / 100).quantize(Decimal("1"))
    d.row([(50, "Total costs if you exit after 1 year", "l"), (W - 50, f"{chf(total_y1)}", "r")])
    d.section("Composition of costs")
    d.row([(50, "One-off costs upon entry or exit", "l")], bold=True)
    d.row([(50, "Entry costs (maximum)", "l"), (W - 50, f"up to {pct(k['entry_max'])}", "r")])
    d.row([(50, "Exit costs", "l"), (W - 50, pct(k["exit"]), "r")])
    d.row([(50, "Ongoing costs taken each year", "l")], bold=True)
    d.row([(50, "Management fees and other administrative or operating costs", "l"), (W - 50, pct(k["ongoing"]), "r")])
    if k["mgmt_included"] is not None:
        d.row([(70, "of which investment management fee", "l"), (W - 50, pct(k["mgmt_included"]), "r")])
    d.row([(50, "Transaction costs", "l"), (W - 50, pct(k["transaction"]), "r")])
    d.row([(50, "Incidental costs taken under specific conditions", "l")], bold=True)
    d.row([(50, "Performance fees", "l"), (W - 50, pct(k["performance"]), "r")])
    d.save()


def termsheet(out: Path):
    t = S.STRUCTURED_TERMSHEET
    d = Doc(out / f"termsheet_{t['isin']}.pdf", "Final terms")
    d.header(t["issuer"], "Synthetic issuer", "Final termsheet", f"{t['name']} · ISIN {t['isin']} · {t['date']}")
    d.kv("Product", t["name"])
    d.kv("ISIN", t["isin"])
    d.kv("Issuer", t["issuer"])
    d.kv("Denomination", "CHF 1'000.00")
    d.section("Costs and fees")
    d.row([(50, "Distribution fee", "l"), (W - 50, f"up to {pct(t['distribution_fee_max'])} p.a.", "r")])
    d.row([(50, "Issuer estimated value / margin", "l"), (W - 50, "not disclosed", "r")])
    d.para("The issue price may include a margin for the issuer that is not separately disclosed.")
    d.save()


def alpha_cash_statement_scanned(out: Path, tmp: Path):
    """Italian-language cash statement, rasterised to an image-only PDF to exercise OCR."""
    import pypdfium2

    src = tmp / "alpha_estratto_conto_digital.pdf"
    d = Doc(src, "Estratto conto")
    d.header(S.ALPHA, S.ALPHA_CITY, "Estratto conto", "Periodo 01.07.2026 - 30.09.2026 · Conto 4512-01 CHF")
    d.kv("Cliente", S.PROSPECT_LABEL)
    d.section("Movimenti")
    d.row([(50, "Data", "l"), (120, "Descrizione", "l"), (W - 50, "Addebito CHF", "r")], bold=True)
    for dt, text, _code, amt in S.ALPHA_CASH_DEBITS:
        y, m, dd = dt.split("-")
        d.row([(50, f"{dd}.{m}.{y}", "l"), (120, text, "l"), (W - 50, chf(amt), "r")])
    d.save()
    pdf = pypdfium2.PdfDocument(str(src))
    images = [pdf[i].render(scale=200 / 72).to_pil().convert("L") for i in range(len(pdf))]
    pdf.close()
    images[0].save(out / "alpha_estratto_conto_Q3_2026_scan.pdf", "PDF", resolution=200.0,
                   save_all=True, append_images=images[1:], title="Estratto conto (scanned)",
                   subject="SYNTHETIC DEMO DOCUMENT", creationDate=None)
    src.unlink()


def beta_holdings_xlsx(out: Path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Holdings"
    ws["A1"] = S.BETA
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = f"{S.BETA_CITY} · Holdings report · SYNTHETIC DEMO DATA"
    ws["A3"] = "Valuation date"
    ws["B3"] = "30.09.2026"
    ws["A4"] = "Reference currency"
    ws["B4"] = "CHF"
    ws["A5"] = "FX rate USD/CHF"
    ws["B5"] = float(S.USD_CHF)  # spreadsheets store binary floats; the parser re-reads cells as text
    headers = ["Description", "ISIN", "Asset class", "Quantity", "Currency", "Price", "Market value (ccy)", "Market value CHF"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=7, column=i, value=h).font = Font(bold=True)
    r = 8
    for p in S.BETA_POSITIONS:
        ws.cell(row=r, column=1, value=p.name)
        ws.cell(row=r, column=2, value=p.isin or "")
        ws.cell(row=r, column=3, value=p.asset_class.title())
        ws.cell(row=r, column=4, value=float(p.quantity) if p.quantity is not None else None)
        ws.cell(row=r, column=5, value=p.ccy)
        ws.cell(row=r, column=6, value=float(p.price) if p.price is not None else None)
        ws.cell(row=r, column=7, value=float(p.value_ccy))
        ws.cell(row=r, column=8, value=float(p.value_chf))
        r += 1
    ws.cell(row=r, column=1, value="Total").font = Font(bold=True)
    ws.cell(row=r, column=8, value=float(S.BETA_TOTAL)).font = Font(bold=True)
    for col, wdt in zip("ABCDEFGH", [40, 16, 12, 10, 9, 10, 18, 18], strict=True):
        ws.column_dimensions[col].width = wdt
    wb.properties.creator = "PortfolioCostEngine synthetic generator"
    wb.save(out / "beta_holdings_2026-09-30.xlsx")


def generate(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / ".tmp"
    tmp.mkdir(exist_ok=True)
    alpha_statement(out)
    alpha_cost_report(out)
    alpha_tariff(out)
    alpha_cash_statement_scanned(out, tmp)
    beta_holdings_xlsx(out)
    beta_lu_tariff(out)
    for isin, k in S.KIDS.items():
        kid(out, isin, k)
    termsheet(out)
    tmp.rmdir()
    return sorted(p for p in out.iterdir() if p.is_file())


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/synthetic/prospect_p1042")
    for p in generate(target):
        print(p)
