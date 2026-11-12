"""Verification of extracted fee values before they reach the totals (SC-5.8).

Every value gets a ``Review``: ``accepted`` or ``needs_review`` with short reason codes the analyst
sees next to the number. Nothing is dropped and nothing is corrected silently: a doubtful value stays
visible, flagged, with the alternative reading when there is one.

Checks:
- second_reader_agrees: a second, independent reader (OCR of the rendered page) reads the same number
  at the same place. Catches text layers that differ from the printed page (hidden layers, bad font
  maps) and OCR misreads on scans. Disagreement or nothing printed there -> needs_review.
- label_on_row: the label came from the value's own row. Recorded, not flagged: on the benchmark a label
  taken from the lines beside the value was right three times in four.
- zero_in_text: a zero printed in running text ("may be 0.00") rather than in a fee table -> needs_review.
  Missing is never zero, so a zero needs a table that states it.
- amount_plausible: an amount of a million or more whose fee word comes only from a section title (an
  annual report's statement of operations, not a client fee) -> needs_review.
- ocr_low_confidence: the value was read by OCR with low confidence -> needs_review.
- separator_ambiguous: an amount printed as "1.250" or "1,250" on a page that does not show which
  separator it uses for decimals -> needs_review (a factor-1000 error is the worst misread).
- rate_in_range: an ongoing annual fee (custody, management, advisory, all-in) above 3 % is unusual
  (a misread decimal, a discount table, a cumulative figure) -> needs_review.
- components_sum_to_total: a "total" row equals the sum of the rows above it in the same column.
  Recorded as a passed check when it holds; never auto-corrected.
"""

from __future__ import annotations

import re
from decimal import Decimal

from .layout import PageInfo
from .models import Check, Fact, Review
from .numbers import find_numbers

LOW_CONFIDENCE = 0.80
MAX_ANNUAL_RATE = Decimal("3")
ONGOING_CODES = {"CUSTODY_FEE", "MGMT_DISCRETIONARY", "ADVISORY_FEE", "ALL_IN_FEE", "ACCOUNT_FEE"}
BIG_AMOUNT = Decimal("1000000")
TOTAL_WORDS = re.compile(r"total|insgesamt|gesamt|summe|totale|totali|totaux|somme", re.I)


def _centre_in(box: list[float], other: tuple[float, float, float, float], pad: float) -> bool:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return other[0] - pad <= cx <= other[2] + pad and other[1] - pad <= cy <= other[3] + pad


def _second_reading(f: Fact, other: list[PageInfo]) -> Check:
    page = next((p for p in other if p.number == f.evidence.page), None)
    box = f.evidence.bbox
    if page is None or not box:
        return Check(name="second_reader_agrees", passed=False, detail="no second reading")
    want = abs(Decimal(f.value))
    printed_digits = re.sub(r"\D", "", str(f.extra.get("printed") or f.value))
    seen: list[str] = []
    for ln in page.lines:
        for c in ln.cells:
            if not _centre_in(box, c.bbox, pad=3):
                continue
            for n in find_numbers(c.text):
                if abs(n.value) == want:
                    return Check(name="second_reader_agrees", passed=True, detail=f"{page.engine}: {n.text}")
                seen.append(n.text)
            # OCR often drops a small decimal point ("0.0%" -> "00%"); the same digits in the same place
            # still prove the printed page shows this number (the text layer gives the separator)
            if (
                page.engine == SECOND_READER
                and printed_digits
                and re.sub(r"\D", "", c.text) == printed_digits
            ):
                return Check(
                    name="second_reader_agrees", passed=True, detail=f"{page.engine}: same digits {c.text}"
                )
    detail = f"{page.engine} read {', '.join(seen)}" if seen else f"{page.engine} read nothing here"
    return Check(name="second_reader_agrees", passed=False, detail=detail)


def _total_checks(facts: list[Fact]) -> dict[str, Check]:
    """Total rows that equal the sum of the same-unit values above them in the same column."""
    out: dict[str, Check] = {}
    by_page: dict[int, list[Fact]] = {}
    for f in facts:
        if f.evidence.page and f.evidence.bbox and f.value is not None:
            by_page.setdefault(f.evidence.page, []).append(f)
    for fs in by_page.values():
        for t in fs:
            if not TOTAL_WORDS.search(t.label.split("|")[0]):
                continue
            tb = t.evidence.bbox
            col = [
                f
                for f in fs
                if f is not t
                and f.field == t.field
                and f.evidence.bbox[3] <= tb[1]
                and min(f.evidence.bbox[2], tb[2]) - max(f.evidence.bbox[0], tb[0]) > 0
                and not TOTAL_WORDS.search(f.label.split("|")[0])
            ]
            if len(col) >= 2 and sum(Decimal(f.value) for f in col) == Decimal(t.value):
                out[t.key] = Check(name="components_sum_to_total", passed=True, detail=f"{len(col)} rows")
    return out


def verify(facts: list[Fact], pages: list[PageInfo], second: list[PageInfo] | None = None) -> list[Fact]:
    """Attach a Review to every fact (in place) and return the facts."""
    totals = _total_checks(facts)
    for f in facts:
        checks: list[Check] = []
        reasons: list[str] = []
        engines = [f.evidence.engine] if f.evidence.engine else []
        alternatives: list[dict] = []
        if second is not None and f.value is not None:
            c = _second_reading(f, second)
            checks.append(c)
            if c.passed:
                engines.append(second[0].engine if second else "")
            else:
                reasons.append(
                    "engines_disagree"
                    if " read " in c.detail and "nothing" not in c.detail
                    else "not_confirmed"
                )
                if "read nothing" not in c.detail and " read " in c.detail:
                    alternatives.append(
                        {"value": c.detail.split(" read ", 1)[1], "engine": c.detail.split(":")[0]}
                    )
        src = f.extra.get("label_source", "row")
        checks.append(Check(name="label_on_row", passed=src == "row", detail=src))
        value = Decimal(f.value) if f.value is not None else None
        if value == 0 and f.evidence.region == "text":
            reasons.append("zero_in_text")
        if (
            value is not None
            and f.field == "amount"
            and abs(value) >= BIG_AMOUNT
            and f.extra.get("fee_context") == "heading"
        ):
            reasons.append("amount_implausible")
        if f.extra.get("separator_ambiguous"):
            reasons.append("separator_ambiguous")  # 1.250 read as 1250: confirm the locale
        if f.evidence.confidence < LOW_CONFIDENCE:
            reasons.append("ocr_low_confidence")
        if (
            f.field == "rate_pct"
            and f.fee_code in ONGOING_CODES
            and value is not None
            and abs(value) > MAX_ANNUAL_RATE
        ):
            reasons.append("rate_out_of_range")
            checks.append(
                Check(name="rate_in_range", passed=False, detail=f"{f.value} % > {MAX_ANNUAL_RATE} %")
            )
        if f.key in totals:
            checks.append(totals[f.key])
        f.review = Review(
            status="needs_review" if reasons else "accepted",
            reasons=reasons,
            engines=[e for e in engines if e],
            alternatives=alternatives,
            checks=checks,
        )
    return facts


SECOND_READER = "tesseract-crops"
_LOOKALIKE = str.maketrans({"O": "0", "o": "0", "D": "0", "l": "1", "I": "1", "|": "1"})


def _digits(text: str) -> str:
    """OCR look-alikes inside numbers ("O USD", "1O,5O") back to digits; words are left alone."""
    return re.sub(
        r"(?<![A-Za-z])[0-9OoDlI|][0-9OoDlI|.,'’ ]*[0-9OoDlI|](?![a-z])"
        r"|(?<![A-Za-z])[OoD](?=\s?(?:%|USD|EUR|CHF|GBP))",
        lambda m: (
            m.group(0).translate(_LOOKALIKE)
            if re.search(r"\d", m.group(0)) or len(m.group(0)) == 1
            else m.group(0)
        ),
        text,
    )


_CROP_DPI = 400  # 6-point table text needs it: at 200 dpi "0.123 %" reads "0.128%"
_PAD = 3.0  # points around a value box
_INK = 200  # grey level above which a pixel is paper (tuned on the benchmark pages: 140-200 read alike)
_PSM = 11  # sparse text: one small value per crop; psm 6 left a third more values unread


def _strip_rules(crop):
    """Whiten table rulings (rows or columns that are mostly ink) that a crop catches at its edges:
    Tesseract reads nothing in a crop framed by lines."""
    w, h = crop.size
    px = crop.load()
    for y in range(h):
        if sum(1 for x in range(w) if px[x, y] == 0) > 0.6 * w:
            for x in range(w):
                px[x, y] = 255
    for x in range(w):
        if sum(1 for y in range(h) if px[x, y] == 0) > 0.6 * h:
            for y in range(h):
                px[x, y] = 255
    return crop


def second_reading(data: bytes, facts: list[Fact], lang: str = "eng+ita+deu+fra") -> list[PageInfo] | None:
    """An independent reading of every value box: each page with values is rendered (pypdfium2), the
    value boxes are cropped, stacked into one strip and read by Tesseract in one call per page.

    It reads the printed pixels, not the text layer, so a text layer that differs from what is printed
    (hidden layers, broken font maps) shows up as a disagreement. Returns ``None`` when Tesseract is not
    installed: the checks are then recorded as not run, never as passed."""
    import shutil

    if shutil.which("tesseract") is None:
        return None
    import io

    import pypdfium2
    import pytesseract
    from PIL import Image

    from .layout import Cell, Line

    by_page: dict[int, list[Fact]] = {}
    for f in facts:
        if f.evidence.page and f.evidence.bbox and f.value is not None:
            by_page.setdefault(f.evidence.page, []).append(f)
    out: list[PageInfo] = []
    pdf = pypdfium2.PdfDocument(io.BytesIO(data))
    try:
        scale = _CROP_DPI / 72
        for number, fs in sorted(by_page.items()):
            page = pdf[number - 1]
            img = page.render(scale=scale).to_pil().convert("L")
            # shaded table cells and grey text defeat Tesseract on small crops: binarise first
            img = img.point(lambda v: 255 if v > _INK else 0)
            crops, spans, y = [], [], 10
            for f in fs:
                x0, y0, x1, y1 = f.evidence.bbox
                box = (
                    max(0, int((x0 - _PAD) * scale)),
                    max(0, int((y0 - _PAD) * scale)),
                    min(img.width, int((x1 + _PAD) * scale)),
                    min(img.height, int((y1 + _PAD) * scale)),
                )
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                crop = _strip_rules(img.crop(box))
                crops.append((crop, y))
                spans.append((y, y + crop.height, f))
                y += crop.height + 24
            if not crops:
                continue
            strip = Image.new("L", (max(c.width for c, _ in crops) + 20, y + 10), 255)
            for crop, top in crops:
                strip.paste(crop, (10, top))
            d = pytesseract.image_to_data(
                strip, lang=lang, config=f"--psm {_PSM}", output_type=pytesseract.Output.DICT
            )
            texts: dict[int, list[str]] = {}
            for i, word in enumerate(d["text"]):
                if not (word or "").strip():
                    continue
                cy = d["top"][i] + d["height"][i] / 2
                for k, (a, b, _f) in enumerate(spans):
                    if a - 4 <= cy <= b + 4:
                        texts.setdefault(k, []).append(word)
                        break
            lines = [
                Line(
                    number, [Cell(_digits(" ".join(texts.get(k, []))), tuple(f.evidence.bbox))], SECOND_READER
                )
                for k, (_a, _b, f) in enumerate(spans)
            ]
            out.append(
                PageInfo(number, float(page.get_width()), float(page.get_height()), SECOND_READER, lines)
            )
    finally:
        pdf.close()
    return out
