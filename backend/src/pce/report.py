"""Client-facing PDF report. Receives the analysis WITHOUT internal economics and
renders only computed, source-linked figures, with their evidence status and caveats."""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

NAVY = HexColor("#0B2545")
TEAL = HexColor("#13706B")
GREY = HexColor("#5B6573")
LINE = HexColor("#D5D9E0")
AMBER = HexColor("#9A6400")
W, H = A4
LAYER_NAMES = {"L1": "Management / advisory", "L2": "Custody & account", "L3": "Trading & FX", "L4": "Funds & ETFs (embedded)",
               "L5": "Structured products (embedded)", "L9": "Taxes on fees"}
BOUND_WORDS = {"point": "", "at_least": "at least ", "at_most": "at most ", "indeterminate": "known-cost difference "}
STATUS = {"observed": "Observed", "contractual": "Contract", "public_tariff": "Public list price", "estimated": "Estimated",
          "unknown": "Unknown"}


def chf(v, dec: int = 0) -> str:
    if v is None:
        return "–"
    d = Decimal(str(v))
    return f"CHF {d:,.{dec}f}".replace(",", "'")


def render_client_report(r: dict) -> bytes:
    assert "internal" not in r, "internal economics must never reach the client report"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, invariant=1)
    c.setTitle(f"Portfolio cost review – {r['prospect']['label']}")
    synthetic = r.get("synthetic") or r["prospect"].get("synthetic")
    approved = bool(r.get("approval") and r["approval"]["valid"])
    firm = r["proposal_inputs"].get("firm_name", "Proposal")
    same = r["scenarios"]["same_holdings"]["comparison"]
    cur = r["scenarios"]["current_comparable"]
    prop = r["scenarios"]["same_holdings"]["ledger"]

    def page_frame(title: str, n: int):
        if synthetic:
            c.saveState()
            c.setFillColor(Color(0.8, 0.15, 0.15, alpha=0.10))
            c.setFont("Helvetica-Bold", 60)
            c.translate(W / 2, H / 2)
            c.rotate(35)
            c.drawCentredString(0, 0, "SYNTHETIC DEMO")
            c.restoreState()
        c.setFillColor(NAVY)
        c.rect(0, H - 6, W, 6, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, H - 30, firm.upper())
        c.setFont("Helvetica", 8)
        c.setFillColor(GREY)
        c.drawRightString(W - 40, H - 30, f"Page {n}")
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40, H - 62, title)
        c.setFont("Helvetica", 9)
        c.setFillColor(AMBER if not approved else TEAL)
        state = (f"APPROVED by {r['approval']['user']} on {r['approval']['at'][:10]}" if approved
                 else "DRAFT – not approved for client use")
        c.drawString(40, H - 78, f"{r['prospect']['label']} · {state}")
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GREY)
        c.drawString(40, 28, "This review compares costs on the basis of the documents provided. It is not investment, tax or "
                             "legal advice. Unknown costs are shown as unknown, never as zero.")
        c.drawString(40, 19, f"Calculation {r['engine_version']} · snapshot {r['snapshot_hash'][:12]}"
                             + (" · All names and figures are synthetic." if synthetic else ""))

    page_frame("Portfolio cost review", 1)
    y = H - 115
    kpis = [
        ("Assets reviewed", chf(r["aum"]["total"]), f"{len(r['institutions'])} banks"),
        ("Current known annual cost", chf(cur["total_known"]),
         f"{cur['total_bps']} bps" + (" · incomplete" if not cur["is_complete"] else "")),
        (f"With {firm}, same holdings", chf(prop["total_known"]), f"{prop['total_bps']} bps"),
        ("Annual saving", BOUND_WORDS[same["bound"]] + chf(same["annual_saving"]),
         f"first year {chf(same['first_year_net'])} after switching costs"),
    ]
    bw = (W - 80 - 30) / 4
    for i, (k, v, sub) in enumerate(kpis):
        x = 40 + i * (bw + 10)
        c.setStrokeColor(LINE)
        c.roundRect(x, y - 58, bw, 62, 4, stroke=1, fill=0)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GREY)
        c.drawString(x + 8, y - 10, k)
        c.setFont("Helvetica-Bold", 12 if len(v) < 18 else 10)
        c.setFillColor(NAVY if i < 3 else TEAL)
        c.drawString(x + 8, y - 30, v)
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        c.drawString(x + 8, y - 46, sub[:42])
    y -= 90

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(NAVY)
    c.drawString(40, y, "Annual cost by layer (like-for-like, same holdings)")
    y -= 16
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(GREY)
    c.drawString(40, y, "Layer")
    c.drawRightString(360, y, "Today")
    c.drawRightString(460, y, firm[:22])
    c.drawRightString(W - 40, y, "Difference")
    y -= 6
    c.setStrokeColor(LINE)
    c.line(40, y, W - 40, y)
    y -= 13
    unknown_layers = {a["layer"] for a in cur["atoms"] if a["role"] == "unknown"}
    for layer, name in LAYER_NAMES.items():
        a = Decimal(cur["by_layer"].get(layer, "0"))
        b = Decimal(prop["by_layer"].get(layer, "0"))
        if a == 0 and b == 0 and layer not in unknown_layers:
            continue
        c.setFont("Helvetica", 8.5)
        c.setFillColor(NAVY)
        c.drawString(40, y, name + (" *" if layer in unknown_layers else ""))
        c.drawRightString(360, y, chf(a))
        c.drawRightString(460, y, chf(b))
        c.drawRightString(W - 40, y, chf(a - b))
        y -= 14
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(40, y, "Total known")
    c.drawRightString(360, y, chf(cur["total_known"]))
    c.drawRightString(460, y, chf(prop["total_known"]))
    c.drawRightString(W - 40, y, chf(same["annual_saving"]))
    y -= 12
    c.setFont("Helvetica", 7)
    c.setFillColor(AMBER)
    if unknown_layers:
        c.drawString(40, y, "* includes costs that could not be quantified from the documents provided (see below).")
        y -= 10
    for ex in r.get("comparison_exclusions", []):
        c.setFillColor(GREY)
        c.drawString(40, y, f"Excluded from comparison: {ex['label']} {chf(ex['amount'])} – {ex['reason']}"[:150])
        y -= 10
    y -= 14

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(NAVY)
    c.drawString(40, y, "What we could not verify yet")
    y -= 15
    c.setFont("Helvetica", 8.5)
    unknowns = [a for a in cur["atoms"] if a["role"] == "unknown"]
    if not unknowns:
        c.setFillColor(TEAL)
        c.drawString(40, y, "All material cost categories are documented.")
        y -= 13
    for a in unknowns[:8]:
        c.setFillColor(NAVY)
        c.drawString(48, y, f"• {a['label']}")
        c.setFillColor(GREY)
        c.drawRightString(W - 40, y, "unknown – not counted as zero")
        y -= 12
    y -= 8
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(NAVY)
    c.drawString(40, y, "Documents that would complete the review")
    y -= 15
    for q in r["requests"][:6]:
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(NAVY)
        c.drawString(48, y, f"{q['priority']}. {q['title']}")
        y -= 11
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GREY)
        c.drawString(60, y, q["ask_for"][:120])
        y -= 13
    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(NAVY)
    c.drawString(40, y, "Assumptions")
    y -= 14
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GREY)
    pi = r["proposal_inputs"]
    notes = [
        f"Fund costs = current position value × ongoing and transaction cost rates from each fund's KID (dated).",
        f"Trading volume assumed equal for both scenarios: turnover {chf(pi['annual_turnover_chf'])}, FX volume {chf(pi['fx_notional_chf'])}.",
        f"Switching costs {chf(same['migration_one_off'])} (transfer fees); payback "
        + (f"{same['payback_months']} months." if same.get("payback_months") else "not reached."),
        f"Client domicile {r['client_domicile']}: Swiss VAT " + ("applied" if r["client_domicile"] == "CH" else "not applied") + " to proposed fees.",
    ] + same["caveats"]
    for n in notes:
        c.drawString(48, y, ("• " + n)[:150])
        y -= 11
    c.showPage()

    page_frame("Appendix – every number and its source", 2)
    y = H - 110
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(GREY)
    for x, t in ((40, "Cost item"), (330, "Status"), (400, "Source"), (W - 40, "CHF / year")):
        (c.drawRightString if x > 500 else c.drawString)(x, y, t)
    y -= 5
    c.line(40, y, W - 40, y)
    y -= 11
    src = {f"{d['id']}": d for d in r.get("documents", [])}
    for a in cur["atoms"]:
        if a["role"] not in ("counted", "unknown"):
            continue
        if y < 60:
            c.showPage()
            page_frame("Appendix (continued)", 3)
            y = H - 110
        c.setFont("Helvetica", 7.5)
        c.setFillColor(NAVY)
        c.drawString(40, y, f"{a['label']} · {a['fee_label']}"[:62])
        c.setFillColor(AMBER if a["role"] == "unknown" else GREY)
        c.drawString(330, y, STATUS.get(a["measurement"], a["measurement"]))
        c.setFillColor(GREY)
        ev = a.get("evidence_sources") or []
        c.drawString(400, y, (ev[0] if ev else "–")[:30])
        c.setFillColor(NAVY)
        c.drawRightString(W - 40, y, "unknown" if a["amount"] is None else chf(a["amount"], 2).replace("CHF ", ""))
        y -= 11
    _ = src
    c.save()
    return buf.getvalue()
