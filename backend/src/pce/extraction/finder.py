"""Layout-aware fee finder that works on any document type and any reader (SC-5.8).

The per-type parsers in ``parsers.py`` know a few layouts well. This finder knows none and
relies on page geometry instead, which is what the SC-5.6 benchmark showed is missing: values
are read almost perfectly, but linking a value to its label fails when the label is not on the
same text line (wrapped row labels, column headers, a section title above a table).

For every rate or amount on a page it builds the label from, in order:
  1. the text left of the value on the same row (the row label),
  2. the nearest label line above when the row has no text (a wrapped or vertically centred label),
  3. the column header above the value (``If you exit after 1 year``, ``Minimum``, ``p.a.``),
  4. the nearest heading above (the section the table belongs to).
A value is a fee candidate when a fee word appears in any of those, and not in a performance
scenario, an invested amount or a tier threshold. Every candidate keeps the boxes of the value,
the label and the row, so the analyst can click a number and see where it came from.

Input is ``PageInfo`` lines (pdfplumber text layer, Tesseract, or any OCR/VLM adapter that gives
boxes); optional layout regions (a layout model's table boxes) narrow the header search.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .layout import Cell, Line, PageInfo
from .models import Evidence, Fact
from .numbers import PrintedNumber, find_numbers
from .vocab import map_fee_label

FINDER_VERSION = "pce-finder-0.1"

FEE_WORDS = re.compile(
    r"fee|cost|charge|commission|expense|\bter\b|\bocf\b|spread|custody|brokerage|safekeeping|tariff|price|"
    r"minimum|geb[üu]hr|kosten|kommission|courtage|depot|spesen|entgelt|aufschlag|preis|tarif|minimal|"
    r"frais|co[uû]ts?\b|droits?\b|garde|tenue|commission|prix|minimum|"
    r"cost[io]|commission[ei]|spes[ae]|oner[ei]|custodia|diritt[oi]|tenuta|prezz[oi]|tariff|minim[oa]|incidenza",
    re.I,
)
# Rows that print numbers next to fee words but are not fees: KID performance scenarios, returns,
# a bank's own fee income in an annual report.
NOT_FEE = re.compile(
    r"scenario|szenario|sc[ée]nario|stress|(?:un)?favou?rable|moderate|pessimist|optimist|"
    r"sfavorevol|favorevol|d[ée]favorable|interm[ée]diaire|mittler|"
    r"rendement|rendimento|rendite\b|average return|might get back|potreste ottenere|pourriez obtenir|"
    r"zur[üu]ckerhalten|what you get|rimborso al netto|net of costs|nach abzug der kosten|"
    r"apr[èe]s d[ée]duction|"
    r"possibile rimborso|isin\b|valor(?:en)?nummer|volatilit|drawdown|sharpe|value at risk|\bvar\b|"
    r"wertentwicklung|realis|realiz|gain|loss|gewinn|verlust|plus-value|moins-value|dividend",
    re.I,
)
INVESTED = re.compile(
    r"invest|anlage(?:betrag|beispiel)|placement|investiss|premio|pr[äa]mie|versamento|einmalanlage|"
    r"montant minimum|mindestanlage|importo minimo di sottoscrizione|conferimento|giacenza|"
    r"mindesteinlage|minimum deposit|d[ée]p[ôo]t minimum",
    re.I,
)
BAND_WORD = re.compile(
    r"(?:\bbis\b|up to|\bab\b|\bfrom\b|\bover\b|\babove\b|fino a|\boltre\b|jusqu|au-del|\bd[èe]s\b|"
    r"\bnext\b|\bfirst\b|between|\bentre\b|\btra\b|[üu]ber|\bunter\b|below|\bsotto\b|\bda\b|[<>≤≥]|"
    r"\bvon\b|\bde\b|\bdi\b|\bto\b|\ba\b|\bà\b|\bje\b|per ogni)[^\d]{0,12}$",
    re.I,
)
PHONE = re.compile(r"(?:tel|fax|phone|t[ée]l[ée]phone|telefon)\b[^\n]{0,12}$|\+\d{0,3}\s*$", re.I)
MILLION = re.compile(r"^\s*(?:mio|million|millionen|milioni|mln|mn|mrd|bn|billion)\b", re.I)
THRESHOLD = 10_000  # a band limit is a large amount; a fee "up to EUR 300" is not


@dataclass
class _Val:
    num: PrintedNumber
    cell: Cell
    bbox: tuple[float, float, float, float]
    weak: bool = False  # a bare integer alone in its cell: a fee only under an amount/currency header


def _has_letters(s: str) -> bool:
    return bool(re.search(r"[^\W\d_]{2,}", s))


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def _num_bbox(cell: Cell, n: PrintedNumber) -> tuple[float, float, float, float]:
    """Box of the number inside its cell, by character share; the cell box when the cell is the number."""
    x0, y0, x1, y1 = cell.bbox
    t = cell.text
    if not t or (n.start == 0 and n.end >= len(t.rstrip())):
        return cell.bbox
    if cell.words:  # exact: the reader's word boxes that the number spans
        ends = [*(o for o, _ in cell.words[1:]), len(t) + 1]
        hit = [b for (o, b), e in zip(cell.words, ends, strict=True) if o < n.end and e - 1 > n.start]
        if hit:
            return (
                min(b[0] for b in hit),
                min(b[1] for b in hit),
                max(b[2] for b in hit),
                max(b[3] for b in hit),
            )
    w = (x1 - x0) / max(len(t), 1)
    return (round(x0 + w * n.start, 2), y0, round(x0 + w * n.end, 2), y1)


def _accepted(n: PrintedNumber, before: str, after: str = "") -> bool:
    """A rate or a money-looking amount. Bare integers (counts, years, footnotes, page numbers),
    rates above 100 % and tier thresholds are not fee values."""
    if n.unit == "bp":
        return n.value <= 1000
    if n.is_rate:
        return abs(n.value) <= 100
    if not n.formatted:
        return False
    if n.currency is None and n.value == n.value.to_integral_value() and 1900 <= n.value <= 2100:
        return False  # a year printed with a separator ("2,025") is rare, a year is not
    if MILLION.match(after) or PHONE.search(before[-20:]):
        return False  # "CHF 2 million" is a band limit, "+41 61 205" a phone number
    if abs(n.value) >= THRESHOLD and (
        BAND_WORD.search(before[-30:])
        or INVESTED.search(before[-25:])
        or re.search(r"minim", before[-40:], re.I)
    ):
        return False  # "bis CHF 500'000" is a band limit, "Anlagebeispiel 10 000 CHF" the example investment
    return not (INVESTED.search(before[-15:]) or INVESTED.match(after.strip()[:12]))


def _bare_amount(n: PrintedNumber, cell_text: str) -> bool:
    """``600`` or ``(600)`` alone in a table cell: maybe an amount, decided later by its column header."""
    return (
        not n.is_rate
        and not n.formatted
        and 10 <= abs(n.value) < 10_000_000
        and not 1900 <= abs(n.value) <= 2100
        and bool(re.fullmatch(r"\(?-?\d+\)?-?", cell_text.strip()))
    )


AMOUNT_HEADER = re.compile(r"\b(?:CHF|EUR|USD|GBP)\b|amount|betrag|importo|montant|€|\$|£", re.I)


def _values(line: Line) -> list[_Val]:
    out = []
    left = ""
    for c in line.cells:
        for n in find_numbers(c.text):
            if n.unit == "" and n.currency is None and MILLION.match(c.text[n.end :]):
                continue
            if _accepted(n, f"{left} {c.text[: n.start]}", c.text[n.end :]):
                out.append(_Val(n, c, _num_bbox(c, n)))
            elif _bare_amount(n, c.text):
                out.append(_Val(n, c, _num_bbox(c, n), weak=True))
        left = f"{left} {c.text}"
    # a band range "500'000 - 1'000'000" is a label, both ends
    big = [v for v in out if not v.num.is_rate and abs(v.num.value) >= THRESHOLD]
    if len(big) >= 2 and re.search(r"\d\s*[-–]\s*(?:CHF|EUR|USD)?\s*\d", line.text):
        out = [v for v in out if v not in big]
    return out


def _height(line: Line) -> float:
    return max(line.bbox[3] - line.bbox[1], 4.0)


def _in(
    box: tuple[float, float, float, float], region: tuple[float, float, float, float], pad: float = 3
) -> bool:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return region[0] - pad <= cx <= region[2] + pad and region[1] - pad <= cy <= region[3] + pad


def _block(column: list[Cell], anchor: Cell, h: float, valued: set[int]) -> list[Cell]:
    """The anchor plus the tightly stacked lines of the same cell above and below it (a wrapped label).
    Growth stops at a gap of about half a line, or at a line that has a value in the same column as the
    value being labelled (that line is another row of the table)."""
    i = column.index(anchor)
    block = [anchor]
    for step in (-1, 1):
        j, last = i + step, anchor
        while 0 <= j < len(column):
            c = column[j]
            gap = (last.bbox[1] - c.bbox[3]) if step < 0 else (c.bbox[1] - last.bbox[3])
            if gap > 0.45 * h or gap < -h or id(c) in valued:
                break
            block.append(c)
            last, j = c, j + step
    return sorted(block, key=lambda c: c.bbox[1])


def _label_cells(
    text_cells: list[Cell], v: _Val, h: float, rows: dict[int, list[tuple[float, float]]]
) -> tuple[list[Cell], list[Cell]]:
    """(label cells, description cells) for a value.

    Label: the text cells left of the value on its row, one block per column (each grown over wrapped
    lines). When the row has no text, the nearest label lines within ~1.5 lines above or below, per
    column (a label printed beside a block of values, or values centred against a wrapped label).
    Long blocks (more than 12 words) are descriptions: kept as context, not as the label."""
    yc = (v.bbox[1] + v.bbox[3]) / 2
    left = [c for c in text_cells if c.bbox[2] <= v.bbox[0] + 1]
    same = [c for c in left if abs((c.bbox[1] + c.bbox[3]) / 2 - yc) <= 0.6 * h]
    pool = same or [c for c in left if abs((c.bbox[1] + c.bbox[3]) / 2 - yc) <= 1.6 * h]
    label: list[Cell] = []
    desc: list[Cell] = []
    seen_cols: list[float] = []
    for c in sorted(pool, key=lambda c: c.bbox[0]):
        if any(abs(c.bbox[0] - x) < 4 for x in seen_cols):
            continue
        seen_cols.append(c.bbox[0])
        col = [d for d in pool if abs(d.bbox[0] - c.bbox[0]) < 4]
        anchor = min(col, key=lambda d: abs((d.bbox[1] + d.bbox[3]) / 2 - yc))
        column = sorted((d for d in left if abs(d.bbox[0] - anchor.bbox[0]) < 4), key=lambda d: d.bbox[1])
        col_x = (v.bbox[0] - 2, v.bbox[2] + 2)
        other_rows = {
            cid
            for cid, spans in rows.items()
            if cid != id(anchor) and any(_overlap(col_x, sp) > 0 for sp in spans)
        }
        block = _block(column, anchor, h, other_rows)
        words = sum(len(d.text.split()) for d in block)
        (desc if words > 12 else label).extend(block)
    return label, desc


def _header_above(
    lines: list[Line], i: int, v: _Val, vals_by_line: list[list[_Val]], region: tuple | None
) -> tuple[str, Cell | None]:
    """Column header: the nearest text above that sits over the value's column, on a line without values
    in that column. Inside a detected table region the search stops at the region's top."""
    col = (v.bbox[0] - 2, v.bbox[2] + 2)
    for j in range(i - 1, max(-1, i - 20), -1):
        if region and not _in(lines[j].bbox, region, pad=12):
            break
        if any(_overlap(col, (w.bbox[0], w.bbox[2])) > 0 for w in vals_by_line[j]):
            continue  # a value of the same column on an earlier row
        hits = [
            c
            for c in lines[j].cells
            if _overlap(col, (c.bbox[0], c.bbox[2])) > 0 and _has_letters(c.text) and not find_numbers(c.text)
        ]
        if hits:
            return hits[0].text, hits[0]
    return "", None


def _heading_above(lines: list[Line], i: int, vals_by_line: list[list[_Val]], limit: int = 40) -> str:
    """Section path above the row: the nearest title line (one cell, short, no values) and, when that
    title has no fee word, the nearest fee-word title above it ("Transaction fees › Equities and bonds")."""
    path: list[str] = []
    for j in range(i - 1, max(-1, i - limit), -1):
        ln = lines[j]
        t = ln.text
        if vals_by_line[j] or len(ln.cells) != 1 or not _has_letters(t) or len(t.split()) > 10:
            continue
        if not path:
            path.append(t)
            if FEE_WORDS.search(t):
                break
        elif FEE_WORDS.search(t):
            path.append(t)
            break
    return " › ".join(reversed(path))


def _union(boxes: list[tuple[float, float, float, float]]) -> list[float]:
    return [
        round(min(b[0] for b in boxes), 2),
        round(min(b[1] for b in boxes), 2),
        round(max(b[2] for b in boxes), 2),
        round(max(b[3] for b in boxes), 2),
    ]


def _decimal_style(lines: list[Line]) -> str | None:
    """The page's decimal separator, from numbers that can only be read one way ("0,85", "12.50")."""
    commas = dots = 0
    for ln in lines:
        commas += len(re.findall(r"(?<![\d.,])\d+,\d{1,2}(?![\d.,])", ln.text))
        dots += len(re.findall(r"(?<![\d.,])\d+\.\d{1,2}(?![\d.,])", ln.text))
    if commas > 2 * dots:
        return ","
    if dots > 2 * commas:
        return "."
    return None


def _ambiguous(n: PrintedNumber, style: str | None) -> bool:
    """ "1.250" or "1,250" as an amount: thousands (1250) or decimals (1.25)? Read as thousands; ambiguous
    unless the page prints its decimals with the other separator."""
    m = re.fullmatch(r"\d{1,3}([.,])\d{3}", re.sub(r"[^\d.,]", "", n.text))
    return bool(m) and not n.is_rate and style in (None, m.group(1))


def _key(page: int, label: str, value: str, y: float) -> str:
    """Stable across re-extraction of the same file: page, label, value and row position."""
    h = hashlib.sha256(f"{page}|{label.lower()}|{value}|{round(y / 4)}".encode()).hexdigest()[:12]
    return f"fee:p{page}:{h}"


def find_fees(
    pages: list[PageInfo],
    regions: dict[int, list[tuple[str, tuple[float, float, float, float]]]] | None = None,
) -> list[Fact]:
    """Fee candidates on every page, each with value, label, row boxes and the label's provenance.

    ``regions`` maps a page number to layout regions ``(label, bbox)`` in PDF points (top-left origin),
    from a layout model; only ``table`` regions are used. Without regions the finder uses geometry alone.
    """
    facts: list[Fact] = []
    for page in pages:
        lines = sorted(page.lines, key=lambda ln: (ln.bbox[1], ln.bbox[0]))
        tables = [b for lab, b in (regions or {}).get(page.number, []) if "table" in lab.lower()]
        vals_by_line = [_values(ln) for ln in lines]
        style = _decimal_style(lines)
        value_cells = {id(v.cell) for vs in vals_by_line for v in vs}
        text_cells = [
            c for ln in lines for c in ln.cells if id(c) not in value_cells and _has_letters(c.text)
        ]
        # for every cell, the x-spans of the values printed on its line (to tell rows apart)
        rows: dict[int, list[tuple[float, float]]] = {}
        for ln, vs in zip(lines, vals_by_line, strict=True):
            for c in ln.cells:
                rows[id(c)] = [(w.bbox[0], w.bbox[2]) for w in vs]
        for i, ln in enumerate(lines):
            h = _height(ln)
            for v in vals_by_line[i]:
                region = next((t for t in tables if _in(v.bbox, t)), None)
                label_cells, desc_cells = _label_cells(text_cells, v, h, rows)
                own = v.cell.text[: v.num.start].strip(" :-–|")
                if _has_letters(own):
                    label_cells = [*label_cells, v.cell]
                label = " ".join(c.text if c is not v.cell else own for c in label_cells).strip()
                yc = (v.bbox[1] + v.bbox[3]) / 2
                on_row = any(abs((c.bbox[1] + c.bbox[3]) / 2 - yc) <= 0.6 * h for c in label_cells)
                source = "row" if on_row else ("near" if label else "header")
                header, header_cell = _header_above(lines, i, v, vals_by_line, region)
                if v.weak and not AMOUNT_HEADER.search(header):
                    continue
                heading = _heading_above(lines, i, vals_by_line)
                context = " ".join(x for x in (label, header, heading) if x)
                if not FEE_WORDS.search(context) or NOT_FEE.search(f"{label} {header}"):
                    continue
                in_table = region is not None or len(ln.cells) >= 2
                full = " › ".join(x for x in (heading, " | ".join(y for y in (label, header) if y)) if x)
                code = map_fee_label(full) or map_fee_label(heading)
                ccy = v.num.currency
                facts.append(
                    Fact(
                        key=_key(page.number, label, v.num.text, v.bbox[1]),
                        kind="fee_mention",
                        field="rate_pct"
                        if v.num.unit == "%"
                        else ("rate_bp" if v.num.unit == "bp" else "amount"),
                        label=full[:200],
                        value=str(v.num.value),
                        currency=ccy,
                        fee_code=code,
                        measurement="observed_in_document",
                        extra={
                            "printed": v.num.text,
                            "heading": heading[:160],
                            "unit": v.num.unit,
                            "label_source": source,
                            "separator_ambiguous": _ambiguous(v.num, style),
                            # where the fee word came from: row label, column header or only the section
                            "fee_context": "label"
                            if FEE_WORDS.search(label)
                            else ("header" if FEE_WORDS.search(header) else "heading"),
                        },
                        evidence=Evidence(
                            page=page.number,
                            bbox=[round(x, 2) for x in v.bbox],
                            page_width=page.width,
                            page_height=page.height,
                            snippet=" ".join([ln.text, header, *(c.text for c in desc_cells)]).strip()[:300],
                            engine=ln.engine,
                            confidence=ln.confidence,
                            label_bbox=_union([c.bbox for c in label_cells]) if label_cells else None,
                            row_bbox=_union([ln.bbox] + [c.bbox for c in label_cells]),
                            region="table" if in_table else "text",
                        ),
                    )
                )
                if header_cell is not None:
                    facts[-1].extra["header_bbox"] = [round(x, 2) for x in header_cell.bbox]
    return _dedupe(facts)


def _dedupe(facts: list[Fact]) -> list[Fact]:
    """One value printed twice at the same spot is one value: PDFs with hidden or duplicated text
    layers draw the same string several times over itself."""
    out: list[Fact] = []
    for f in facts:
        b = f.evidence.bbox
        dup = next(
            (
                g
                for g in out
                if g.evidence.page == f.evidence.page
                and g.value == f.value
                and b
                and g.evidence.bbox
                and _overlap((b[0], b[2]), (g.evidence.bbox[0], g.evidence.bbox[2])) > 0.5 * (b[2] - b[0])
                and _overlap((b[1], b[3]), (g.evidence.bbox[1], g.evidence.bbox[3])) > 0.5 * (b[3] - b[1])
            ),
            None,
        )
        if dup is None:
            out.append(f)
        else:
            dup.extra["duplicates"] = dup.extra.get("duplicates", 0) + 1
    return out
