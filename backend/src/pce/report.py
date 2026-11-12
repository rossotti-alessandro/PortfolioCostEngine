"""Client-facing PDF report. Receives the analysis WITHOUT internal economics and
renders only computed, source-linked figures, with their evidence status and caveats.

Laid out with reportlab platypus so long names and sources wrap instead of being cut, and tables
continue on the next page. English and Italian; Italian first for Lugano prospects."""

from __future__ import annotations

import io
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# docs/design/DESIGN_SYSTEM.md tokens: primary, accent, text-muted, border, warning
NAVY = HexColor("#0F2A4A")
TEAL = HexColor("#0F766E")
GREY = HexColor("#5B6676")
LINE = HexColor("#DEDAD1")
AMBER = HexColor("#B45309")
PAPER = HexColor("#F7F5F0")
PRODUCT_NAME = "FeeLens"
W, H = A4
M = 40  # page margin
LAYER_NAMES = {
    "L1": "Management / advisory",
    "L2": "Custody & account",
    "L3": "Trading & FX",
    "L4": "Funds & ETFs (embedded)",
    "L5": "Structured products (embedded)",
    "L9": "Taxes on fees",
}
BOUND_WORDS = {"point": "", "at_least": "at least", "at_most": "at most", "indeterminate": "known costs only"}
STATUS = {
    "observed": "Observed",
    "contractual": "Contract",
    "public_tariff": "Public list price",
    "estimated": "Estimated",
    "unknown": "Unknown",
}

IT = {
    "Portfolio cost review": "Analisi dei costi del portafoglio",
    "Appendix – every number and its source": "Allegato – ogni cifra e la sua fonte",
    "DRAFT – not approved for client use": "BOZZA – non approvata per il cliente",
    "APPROVED by {user} on {date}": "APPROVATA da {user} il {date}",
    "Page {n}": "Pagina {n}",
    "This review compares costs on the basis of the documents provided. It is not investment, tax or "
    "legal advice. Unknown costs are shown as unknown, never as zero.": "Questa analisi confronta i costi "
    "sulla base dei documenti forniti. Non è una consulenza in materia di investimenti, fiscale o legale. "
    "I costi sconosciuti sono indicati come tali, mai come zero.",
    "All names and figures are synthetic.": "Tutti i nomi e le cifre sono fittizi.",
    "calculation": "calcolo",
    "Assets reviewed": "Patrimonio analizzato",
    "{n} banks": "{n} banche",
    "Current known annual cost": "Costo annuo noto oggi",
    "incomplete": "incompleto",
    "With {firm}, same holdings": "Con {firm}, stesse posizioni",
    "Annual saving": "Risparmio annuo",
    "Proposal costs more per year": "La proposta costa di più all'anno",
    "first year {amount} after switching costs": "primo anno {amount} dopo i costi di trasferimento",
    "at least": "almeno",
    "at most": "al massimo",
    "known costs only": "solo costi noti",
    "What these figures rest on": "Su cosa si basano queste cifre",
    "{facts} values read from {docs} documents · {checked} checked by a person · {open} points still to "
    "review.": "{facts} valori letti da {docs} documenti · {checked} verificati da una persona · {open} "
    "punti ancora da verificare.",
    "Values not yet checked by a person are read automatically from the documents and shown with their "
    "page in the appendix.": "I valori non ancora verificati da una persona sono letti automaticamente dai "
    "documenti e indicati con la loro pagina nell'allegato.",
    "Annual cost by layer (like-for-like, same holdings)": "Costo annuo per livello (a parità di posizioni)",
    "Layer": "Livello",
    "Today": "Oggi",
    "Difference": "Differenza",
    "Total known": "Totale noto",
    "* includes costs that could not be quantified from the documents provided (see below).": "* comprende "
    "costi che non è stato possibile quantificare dai documenti forniti (vedi sotto).",
    "Excluded from comparison: {label} {amount} – "
    "{reason}": "Escluso dal confronto: {label} {amount} – {reason}",
    "What we could not verify yet": "Cosa non abbiamo ancora potuto verificare",
    "All material cost categories are documented.": "Tutte le categorie di costo rilevanti sono documentate.",
    "unknown – not counted as zero": "sconosciuto – non contato come zero",
    "Documents that would complete the review": "Documenti che completerebbero l'analisi",
    "Assumptions": "Ipotesi",
    "Fund costs = current position value × ongoing and transaction cost rates from each fund's KID "
    "(dated).": "Costi dei fondi = valore attuale della posizione × costi correnti e di transazione dal KID "
    "di ciascun fondo (datato).",
    "Trading volume assumed equal for both scenarios: turnover {turnover}, FX volume {fx}.": "Volume di "
    "negoziazione ipotizzato uguale nei due scenari: turnover {turnover}, volume cambi {fx}.",
    "Switching costs {amount} (transfer fees); payback {payback}": "Costi di trasferimento {amount}; "
    "recupero {payback}",
    "{n} months.": "{n} mesi.",
    "not reached.": "non raggiunto.",
    "Client domicile {code}: Swiss VAT applied to proposed fees.": "Domicilio del cliente {code}: IVA "
    "svizzera applicata alle commissioni proposte.",
    "Client domicile {code}: Swiss VAT not applied to proposed fees.": "Domicilio del cliente {code}: IVA "
    "svizzera non applicata alle commissioni proposte.",
    "Some current costs are unknown; the true saving is likely higher than shown.": "Alcuni costi attuali "
    "sono sconosciuti; il risparmio reale è probabilmente superiore a quello indicato.",
    "Some proposal costs are unknown; the true saving may be lower than shown.": "Alcuni costi della "
    "proposta sono sconosciuti; il risparmio reale potrebbe essere inferiore a quello indicato.",
    "Both sides have unknown costs; the difference shown covers known costs only.": "Entrambi i lati hanno "
    "costi sconosciuti; la differenza indicata riguarda solo i costi noti.",
    "No annual saving on known costs: the proposal is not cheaper on this evidence.": "Nessun risparmio "
    "annuo sui costi noti: su queste evidenze la proposta non è più economica.",
    "Cost item": "Voce di costo",
    "Status": "Stato",
    "Source": "Fonte",
    "CHF / year": "CHF / anno",
    "unknown": "sconosciuto",
    "Costs are not calculated yet": "I costi non sono ancora calcolati",
    "No statement of assets was provided. Without the positions no cost can be put in proportion to "
    "assets, so no total is shown (not zero).": "Non è stato fornito alcun estratto patrimoniale. Senza le "
    "posizioni nessun costo può essere rapportato al patrimonio, quindi non viene mostrato alcun totale "
    "(non zero).",
    "Management / advisory": "Gestione / consulenza",
    "Custody & account": "Custodia e conto",
    "Trading & FX": "Negoziazione e cambi",
    "Funds & ETFs (embedded)": "Fondi ed ETF (nel NAV)",
    "Structured products (embedded)": "Prodotti strutturati (nel prezzo)",
    "Taxes on fees": "Imposte sulle commissioni",
    "Observed": "Osservato",
    "Contract": "Contratto",
    "Public list price": "Tariffa pubblica",
    "Estimated": "Stimato",
    "Unknown": "Sconosciuto",
}


def chf(v, dec: int = 0) -> str:
    if v is None:
        return "–"
    d = Decimal(str(v))
    return f"CHF {d:,.{dec}f}".replace(",", "'")


def saving_parts(amount: str, bound: str) -> tuple[bool, str, str, str]:
    """(saves, label, bound word, amount). A dearer proposal is never a saving: it reads
    'proposal costs more', and the bound flips with the sign (saving at least -X = costs at most X more)."""
    d = Decimal(str(amount))
    if d >= 0:
        return d > 0, "Annual saving", BOUND_WORDS.get(bound, ""), str(d)
    flip = {"at_least": "at_most", "at_most": "at_least"}
    return False, "Proposal costs more per year", BOUND_WORDS.get(flip.get(bound, bound), ""), str(-d)


def _styles():
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=11, textColor=NAVY)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=7.5, leading=9.5, textColor=GREY),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22),
        "h2": ParagraphStyle(
            "h2",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "kpi_label": ParagraphStyle("kl", parent=base, fontSize=7.5, leading=9, textColor=GREY),
        "kpi": ParagraphStyle("kv", parent=base, fontName="Helvetica-Bold", fontSize=12.5, leading=15),
        "cell": ParagraphStyle("cell", parent=base, fontSize=7.5, leading=9.5),
        "cell_r": ParagraphStyle("cellr", parent=base, fontSize=7.5, leading=9.5, alignment=2),
        "head": ParagraphStyle("head", parent=base, fontName="Helvetica-Bold", fontSize=7.5, textColor=GREY),
        "head_r": ParagraphStyle(
            "headr", parent=base, fontName="Helvetica-Bold", fontSize=7.5, textColor=GREY, alignment=2
        ),
    }


def render_client_report(r: dict, lang: str = "en") -> bytes:
    assert "internal" not in r, "internal economics must never reach the client report"

    def tr(en: str, **kw) -> str:
        s = IT.get(en, en) if lang == "it" else en
        return s.format(**kw) if kw else s

    S = _styles()

    def p(text: str, style: str = "base", color=None) -> Paragraph:
        st = S[style] if color is None else ParagraphStyle(f"{style}-c", parent=S[style], textColor=color)
        return Paragraph(escape(text), st)

    synthetic = r.get("synthetic") or r["prospect"].get("synthetic")
    approved = bool(r.get("approval") and r["approval"]["valid"])
    firm = r["proposal_inputs"].get("firm_name", "Proposal")
    same = r["scenarios"]["same_holdings"]["comparison"]
    cur = r["scenarios"]["current_comparable"]
    prop = r["scenarios"]["same_holdings"]["ledger"]
    state = (
        tr("APPROVED by {user} on {date}", user=r["approval"]["user"], date=r["approval"]["at"][:10])
        if approved
        else tr("DRAFT – not approved for client use")
    )

    def frame(c, doc):
        n = doc.page
        c.saveState()
        if synthetic:
            c.setFillColor(Color(0.8, 0.15, 0.15, alpha=0.10))
            c.setFont("Helvetica-Bold", 60)
            c.translate(W / 2, H / 2)
            c.rotate(35)
            c.drawCentredString(0, 0, "SYNTHETIC DEMO")
            c.rotate(-35)
            c.translate(-W / 2, -H / 2)
        c.setFillColor(NAVY)
        c.rect(0, H - 6, W, 6, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(M, H - 30, firm.upper())
        c.setFont("Helvetica", 8)
        c.setFillColor(GREY)
        c.drawRightString(W - M, H - 30, tr("Page {n}", n=n))
        if n == 1:  # later pages carry their own heading in the flow (overflow pages need none)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(M, H - 62, tr("Portfolio cost review"))
        c.setFont("Helvetica", 9)
        c.setFillColor(TEAL if approved else AMBER)
        c.drawString(M, H - 78 if n == 1 else H - 44, f"{r['prospect']['label']} · {state}")
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GREY)
        c.drawString(
            M,
            28,
            tr(
                "This review compares costs on the basis of the documents provided. It "
                "is not investment, tax "
                "or legal advice. Unknown costs are shown as unknown, never as zero."
            ),
        )
        c.drawString(
            M,
            19,
            f"{PRODUCT_NAME} · {tr('calculation')} {r['engine_version']} · snapshot {r['snapshot_hash'][:12]}"
            + (f" · {tr('All names and figures are synthetic.')}" if synthetic else ""),
        )
        c.restoreState()

    def table(rows, widths, right_from: int, zebra: bool = False, total: bool = False) -> Table:
        t = Table(rows, colWidths=widths, repeatRows=1)
        style = [
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
        if total:
            style.append(("LINEABOVE", (0, -1), (-1, -1), 0.6, NAVY))
        if zebra:
            style += [("BACKGROUND", (0, i), (-1, i), PAPER) for i in range(2, len(rows), 2)]
        t.setStyle(TableStyle(style))
        return t

    story: list = []
    usable = W - 2 * M - 12  # frame padding is 6 pt each side

    def bold(cells: list[str], right_from: int) -> list[Paragraph]:
        return [
            Paragraph(f"<b>{escape(x)}</b>", S["cell_r"] if i >= right_from else S["cell"])
            for i, x in enumerate(cells)
        ]

    def cells(row: list[str], right_from: int, color=None) -> list[Paragraph]:
        return [p(x, "cell_r" if i >= right_from else "cell", color) for i, x in enumerate(row)]

    if not r.get("holdings"):
        # No positions: nothing to put costs in proportion to. Say so; never print CHF 0 as a cost.
        story += [
            p(tr("Costs are not calculated yet"), "h2"),
            p(
                tr(
                    "No statement of assets was provided. Without the positions no cost can be put in "
                    "proportion to assets, so no total is shown (not zero)."
                )
            ),
        ]
    else:
        saves, label, word, amount = saving_parts(same["annual_saving"], same["bound"])
        kpis = [
            (tr("Assets reviewed"), chf(r["aum"]["total"]), tr("{n} banks", n=len(r["institutions"])), NAVY),
            (
                tr("Current known annual cost"),
                chf(cur["total_known"]),
                f"{cur['total_bps']} bps" + ("" if cur["is_complete"] else f" · {tr('incomplete')}"),
                NAVY,
            ),
            (
                tr("With {firm}, same holdings", firm=firm),
                chf(prop["total_known"]),
                f"{prop['total_bps']} bps",
                NAVY,
            ),
            (
                tr(label),
                f"{tr(word)} {chf(amount)}".strip() if word else chf(amount),
                tr("first year {amount} after switching costs", amount=chf(same["first_year_net"]))
                if saves
                else "",
                TEAL if saves else NAVY,
            ),
        ]
        box = [
            [p(k, "kpi_label"), Spacer(1, 3), p(v, "kpi", col), Spacer(1, 2), p(sub, "small")]
            for k, v, sub, col in kpis
        ]
        kt = Table([box], colWidths=[(usable - 24) / 4] * 4)
        kt.setStyle(
            TableStyle(
                [("BOX", (i, 0), (i, 0), 0.6, LINE) for i in range(4)]
                + [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story += [Spacer(1, 4), kt]

        rv = r.get("review") or {"facts": 0, "reviewed": 0, "rejected": 0}
        checked = rv["reviewed"] + rv["rejected"]
        story += [
            p(tr("What these figures rest on"), "h2"),
            p(
                tr(
                    "{facts} values read from {docs} documents · {checked} checked by a "
                    "person · {open} points "
                    "still to review.",
                    facts=rv["facts"],
                    docs=len(r.get("documents", [])),
                    checked=checked,
                    open=len(r.get("review_points", [])),
                ),
                color=TEAL if rv["facts"] and checked >= rv["facts"] else AMBER,
            ),
        ]
        if checked < rv["facts"]:
            story.append(
                p(
                    tr(
                        "Values not yet checked by a person are read automatically from the "
                        "documents and shown "
                        "with their page in the appendix."
                    ),
                    "small",
                )
            )

        story.append(p(tr("Annual cost by layer (like-for-like, same holdings)"), "h2"))
        unknown_layers = {a["layer"] for a in cur["atoms"] if a["role"] == "unknown"}
        rows = [
            [
                p(tr("Layer"), "head"),
                p(tr("Today"), "head_r"),
                p(firm, "head_r"),
                p(tr("Difference"), "head_r"),
            ]
        ]
        for layer, name in LAYER_NAMES.items():
            a = Decimal(cur["by_layer"].get(layer, "0"))
            b = Decimal(prop["by_layer"].get(layer, "0"))
            if a == 0 and b == 0 and layer not in unknown_layers:
                continue
            rows.append(
                cells([tr(name) + (" *" if layer in unknown_layers else ""), chf(a), chf(b), chf(a - b)], 1)
            )
        rows.append(
            bold(
                [
                    tr("Total known"),
                    chf(cur["total_known"]),
                    chf(prop["total_known"]),
                    chf(same["annual_saving"]),
                ],
                1,
            )
        )
        story.append(table(rows, [usable * 0.43, usable * 0.19, usable * 0.19, usable * 0.19], 1, total=True))
        if unknown_layers:
            story.append(
                p(
                    tr(
                        "* includes costs that could not be quantified from the documents "
                        "provided (see below)."
                    ),
                    "small",
                    AMBER,
                )
            )
        for ex in r.get("comparison_exclusions", []):
            story.append(
                p(
                    tr(
                        "Excluded from comparison: {label} {amount} – {reason}",
                        label=ex["label"],
                        amount=chf(ex["amount"]),
                        reason=ex["reason"],
                    ),
                    "small",
                )
            )

        story.append(p(tr("What we could not verify yet"), "h2"))
        unknowns = [a for a in cur["atoms"] if a["role"] == "unknown"]
        if not unknowns:
            story.append(p(tr("All material cost categories are documented."), color=TEAL))
        for a in unknowns:
            story.append(
                Table(
                    [
                        [
                            p(f"• {a['label']} · {a['fee_label']}"),
                            p(tr("unknown – not counted as zero"), "small", AMBER),
                        ]
                    ],
                    colWidths=[usable * 0.68, usable * 0.32],
                    style=[
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ],
                )
            )

        if r["requests"]:
            story.append(p(tr("Documents that would complete the review"), "h2"))
            for q in r["requests"]:
                story.append(
                    KeepTogether(
                        [
                            Paragraph(f"<b>{q['priority']}. {escape(q['title'])}</b>", S["base"]),
                            p(q["ask_for"], "small"),
                            Spacer(1, 3),
                        ]
                    )
                )

        pi = r["proposal_inputs"]
        notes = [
            tr(
                "Fund costs = current position value × ongoing and transaction cost "
                "rates from each fund's KID "
                "(dated)."
            ),
            tr(
                "Trading volume assumed equal for both scenarios: turnover {turnover}, FX volume {fx}.",
                turnover=chf(pi["annual_turnover_chf"]),
                fx=chf(pi["fx_notional_chf"]),
            ),
            tr(
                "Switching costs {amount} (transfer fees); payback {payback}",
                amount=chf(same["migration_one_off"]),
                payback=tr("{n} months.", n=same["payback_months"])
                if same.get("payback_months")
                else tr("not reached."),
            ),
            tr(
                "Client domicile {code}: Swiss VAT applied to proposed fees."
                if r["client_domicile"] == "CH"
                else "Client domicile {code}: Swiss VAT not applied to proposed fees.",
                code=r["client_domicile"],
            ),
        ] + [tr(x) for x in same["caveats"]]
        story.append(p(tr("Assumptions"), "h2"))
        story += [p(f"• {n}", "small") for n in notes]

        # Appendix: every counted or unknown line, full name, status and the page it was read from.
        story += [PageBreak(), p(tr("Appendix – every number and its source"), "h1"), Spacer(1, 8)]
        rows = [
            [
                p(tr("Cost item"), "head"),
                p(tr("Status"), "head"),
                p(tr("Source"), "head"),
                p(tr("CHF / year"), "head_r"),
            ]
        ]
        for a in cur["atoms"]:
            if a["role"] not in ("counted", "unknown"):
                continue
            unknown = a["role"] == "unknown"
            ev = a.get("evidence_sources") or []
            rows.append(
                [
                    p(f"{a['label']} · {a['fee_label']}", "cell"),
                    p(tr(STATUS.get(a["measurement"], a["measurement"])), "cell", AMBER if unknown else GREY),
                    p("; ".join(ev) if ev else "–", "cell", GREY),
                    p(
                        tr("unknown") if a["amount"] is None else chf(a["amount"], 2).replace("CHF ", ""),
                        "cell_r",
                    ),
                ]
            )
        story.append(table(rows, [usable * 0.42, usable * 0.13, usable * 0.32, usable * 0.13], 3, zebra=True))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=M,
        rightMargin=M,
        topMargin=95,
        bottomMargin=48,
        title=f"{PRODUCT_NAME} – {tr('Portfolio cost review')} – {r['prospect']['label']}",
        invariant=1,
    )
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()
