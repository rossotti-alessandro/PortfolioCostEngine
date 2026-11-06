"""Score every engine's outputs against the hand-checked ground truth (SC-5.6).

Ground truth (groundtruth.json, committed) lists, per page, every fee figure printed on
it: label and value as printed, whether it sits in a table, and the value's box taken
from the PDF text layer (pdfplumber words, PDF points, top-left origin).

Metrics per engine (only on pages the engine ran):
  value_recall     GT fee values whose number appears anywhere in the engine's text
  pair_recall      GT fees whose value and >= half of the label words land on the same
                   line or table row (row integrity: what a fee parser needs)
  table_pair_recall  pair_recall restricted to fees printed inside tables
  located          GT values the engine also boxed: a box whose text holds the number
                   and whose area contains the value's centre
  located_tight    same, and the box is at most 3 lines high (word or line level)
  roi_recall       layout engines: GT values inside any detected region / inside a
                   table region (table_roi_recall)
  extract_precision / extract_recall  the shared fee-line extractor (fees.py) run on
                   the engine's text, or the engine's own fee list when it gives one
  text_f1          word bag F1 against the PDF text layer (born-digital pages only)
  sec_per_page     median wall time per page, model load excluded; peak_rss_gb

Usage: python data/specimens/ocrbench/score.py  -> var/ocrbench/scores.json + SCORES.md
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import adapters  # noqa: E402
import fees  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "var" / "ocrbench" / "out"
HERE = Path(__file__).parent
PAGES_JSON = HERE / "pages.json"
GT_JSON = HERE / "groundtruth.json"
SCORES_JSON = ROOT / "var" / "ocrbench" / "scores.json"
SCORES_MD = HERE / "SCORES.md"
S = adapters.SCALE


def page_lines(res: dict) -> list[str]:
    """Every line or table row an engine produced, as plain text."""
    lines = [ln for ln in adapters.strip_markup(res.get("text", "")).splitlines() if ln.strip()]
    for t in res.get("tables", []):
        lines += [" | ".join(c or "" for c in row) for row in t["rows"]]
    lines += [w["t"] for w in res.get("words", [])]
    lines += visual_rows(res.get("words", []))
    lines += [f"{f['label']} {f['value']}" for f in res.get("fees", [])]
    return lines


def visual_rows_boxes(words: list[dict]) -> list[list[dict]]:
    """Group boxed text into visual rows (same baseline band).

    OCR engines return one box per text run, so a table row's label and value come back as
    separate items. Any pipeline would rebuild rows from the boxes; this is the simplest such step.
    """
    rows: list[list[dict]] = []
    for w in sorted((w for w in words if w.get("b")), key=lambda w: (w["b"][1] + w["b"][3]) / 2):
        cy, h = (w["b"][1] + w["b"][3]) / 2, max(4.0, w["b"][3] - w["b"][1])
        if h > 80:  # a block or table box, not a text line
            continue
        if rows:
            last = rows[-1]
            ly = sum((x["b"][1] + x["b"][3]) / 2 for x in last) / len(last)
            if abs(cy - ly) <= 0.5 * h:
                last.append(w)
                continue
        rows.append([w])
    return [sorted(r, key=lambda x: x["b"][0]) for r in rows]


def visual_rows(words: list[dict]) -> list[str]:
    return [" ".join(x["t"] for x in r) for r in visual_rows_boxes(words)]


def has_number(text: str, key: str) -> bool:
    return any(fees.same_number(key, n) for n in fees.numbers(text))


def pair_found(lines: list[str], gt: dict, key: str) -> bool:
    need = fees.label_tokens(gt["label"])
    for ln in lines:
        if not has_number(ln, key):
            continue
        if not need:
            return True
        got = fees.label_tokens(ln)
        if len(need & got) >= max(1, len(need) / 2):
            return True
    return False


def centre_in(box: list[float], pt: tuple[float, float]) -> bool:
    return box[0] - 2 <= pt[0] <= box[2] + 2 and box[1] - 2 <= pt[1] <= box[3] + 2


def tokens(text: str) -> Counter:
    return Counter(re.findall(r"[a-zà-ÿ0-9]+", (text or "").lower()))


def f1(pred: Counter, ref: Counter) -> float:
    tp = sum((pred & ref).values())
    if not tp:
        return 0.0
    p, r = tp / sum(pred.values()), tp / sum(ref.values())
    return 2 * p * r / (p + r)


def score_page(res: dict, gt_items: list[dict], ref_text: str | None) -> dict:
    lines = page_lines(res)
    full = "\n".join(lines)
    boxes = [(w["b"], w["t"]) for w in res.get("words", [])]
    boxes += [(f["b"], f"{f['label']} {f['value']}") for f in res.get("fees", []) if f.get("b")]
    boxes += [(r["b"], r.get("text", "")) for r in res.get("regions", []) if r.get("text")]
    regions = res.get("regions", [])
    table_regs = [r["b"] for r in regions if "table" in r["label"].lower() or r["label"] == "otsl"]
    table_regs += [t["b"] for t in res.get("tables", []) if t.get("b")]
    c = Counter()
    flags = []
    for g in gt_items:
        key = fees.value_key(g["value"])
        if key is None:
            flags.append(None)
            continue
        f = {"v": has_number(full, key), "p": False, "l": False, "t": False}
        flags.append(f)
        c["gt"] += 1
        c["value"] += f["v"]
        p = f["p"] = pair_found(lines, g, key)
        c["pair"] += p
        if g.get("in_table"):
            c["gt_table"] += 1
            c["table_pair"] += p
        if g.get("bbox"):
            c["gt_boxed"] += 1
            x0, y0, x1, y1 = (v * S for v in g["bbox"])
            ctr, h = ((x0 + x1) / 2, (y0 + y1) / 2), (y1 - y0)
            hits = [b for b, t in boxes if b and centre_in(b, ctr) and has_number(t, key)]
            f["l"] = bool(hits)
            f["t"] = any((b[3] - b[1]) <= 3.5 * max(h, 8) for b in hits)
            c["located"] += f["l"]
            c["located_tight"] += f["t"]
            c["roi"] += any(centre_in(r["b"], ctr) for r in regions)
            if g.get("in_table"):
                c["gt_table_boxed"] += 1
                c["table_roi"] += any(centre_in(b, ctr) for b in table_regs)
    # extraction precision / recall: the engine's own fee list if it has one, else the shared extractor
    gt_keys = [k for k in (fees.value_key(g["value"]) for g in gt_items) if k]
    own = res.get("fees")
    if own:
        preds = [k for f in own for k in fees.numbers(f["value"])[:1]]
        preds2 = preds
    else:
        preds = [i["value"] for i in fees.extract_fee_lines(full)]
        preds2 = preds + [i["value"] for i in fees.extract_fee_tables(res.get("tables", []), res.get("text", "")[:3000])]
    tp, npred = match(preds, gt_keys)
    tp2, npred2 = match(preds2, gt_keys)
    c["pred"] += npred
    c["tp"] += tp
    c["pred2"] += npred2
    c["tp2"] += tp2
    c["gt_distinct"] += len(gt_keys)
    # structure: the fee's value and label in one row of an engine-produced table
    trows = [" | ".join(c_ or "" for c_ in row) for t in res.get("tables", []) for row in t["rows"]]
    for g, f in zip([g for g in gt_items if fees.value_key(g["value"])], [f for f in flags if f]):
        if g.get("in_table"):
            f["s"] = pair_found(trows, g, fees.value_key(g["value"]))
            c["table_struct"] += f["s"]
    out = dict(c)
    if ref_text is not None:
        out["text_f1"] = round(f1(tokens(adapters.strip_markup(res.get("text", "")) or full), tokens(ref_text)), 3)
    out["regions"] = len(regions)
    out["tables"] = len(res.get("tables", []))
    out["items"] = flags
    out["false_pos"] = npred - tp
    return out


def match(preds: list[str], gt_keys: list[str]) -> tuple[int, int]:
    """(true positives, distinct predictions): each GT value matched at most once."""
    used = [False] * len(gt_keys)
    tp = 0
    distinct = list(dict.fromkeys(preds))
    for v in distinct:
        for i, k in enumerate(gt_keys):
            if not used[i] and fees.same_number(k, v):
                used[i] = True
                tp += 1
                break
    return tp, len(distinct)


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def main() -> None:
    pages = {p["id"]: p for p in json.loads(PAGES_JSON.read_text(encoding="utf-8"))}
    gt = json.loads(GT_JSON.read_text(encoding="utf-8"))["pages"]
    ref = {}
    for pid, p in pages.items():
        if p["text_layer"] and p["variant"] == "original":
            ref[pid] = json.loads((OUT / "pdfplumber" / f"{pid}.json").read_text())["text"] \
                if (OUT / "pdfplumber" / f"{pid}.json").exists() else None
    engines = {}
    per_page = {}
    for d in sorted(OUT.iterdir()):
        if not d.is_dir() or not (d / "_run.json").exists():
            continue
        meta = json.loads((d / "_run.json").read_text())
        tot = Counter()
        f1s, secs, errors = [], [], 0
        for pid, p in pages.items():
            f = d / f"{pid}.json"
            gt_key = p.get("gt_from", pid)
            if not f.exists() or gt_key not in gt:
                continue
            res = json.loads(f.read_text())
            errors += bool(res.get("error"))
            s = score_page(res, gt[gt_key]["items"], ref.get(pid))
            per_page.setdefault(pid, {})[d.name] = s
            if "text_f1" in s and d.name != "pdfplumber":
                f1s.append(s["text_f1"])
            for k, v in s.items():
                if k not in ("text_f1", "items"):
                    tot[k] += v
            if not res.get("includes_load"):
                secs.append(res["seconds"])
            tot["pages"] += 1
        if not tot["pages"]:
            continue
        engines[d.name] = {
            "engine": d.name, "family": meta.get("family"), "repo": meta.get("repo"),
            "licence": meta.get("licence"), "pages": tot["pages"], "errors": errors,
            "value_recall": ratio(tot["value"], tot["gt"]),
            "pair_recall": ratio(tot["pair"], tot["gt"]),
            "table_pair_recall": ratio(tot["table_pair"], tot["gt_table"]),
            "located": ratio(tot["located"], tot["gt_boxed"]),
            "located_tight": ratio(tot["located_tight"], tot["gt_boxed"]),
            "roi_recall": ratio(tot["roi"], tot["gt_boxed"]),
            "table_roi_recall": ratio(tot["table_roi"], tot["gt_table_boxed"]),
            "extract_precision": ratio(tot["tp"], tot["pred"]),
            "extract_recall": ratio(tot["tp"], tot["gt_distinct"]),
            "extract2_precision": ratio(tot["tp2"], tot["pred2"]),
            "extract2_recall": ratio(tot["tp2"], tot["gt_distinct"]),
            "table_struct_recall": ratio(tot["table_struct"], tot["gt_table"]),
            "text_f1": round(statistics.mean(f1s), 3) if f1s else None,
            "sec_per_page": round(statistics.median(secs), 2) if secs else None,
            "peak_rss_gb": meta.get("peak_rss_gb"),
            "gt_items": tot["gt"],
        }
    SCORES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCORES_JSON.write_text(json.dumps({"engines": engines, "per_page": per_page}, indent=1), encoding="utf-8")
    write_md(engines)
    print(SCORES_MD.read_text(encoding="utf-8"))


def pct(v: float | None) -> str:
    return "–" if v is None else f"{v * 100:.0f}%"


def write_md(engines: dict) -> None:
    cols = [("value_recall", "Values read"), ("pair_recall", "Label+value same row"),
            ("table_struct_recall", "In a table row"), ("located_tight", "Value boxed (tight)"),
            ("table_roi_recall", "Table ROI hit"), ("extract_precision", "Extract precision"),
            ("extract_recall", "Extract recall"), ("extract2_precision", "Table-aware precision"),
            ("extract2_recall", "Table-aware recall"), ("text_f1", "Text F1")]
    lines = ["# Local OCR / layout / VLM benchmark — scores", "",
             "Generated by `data/specimens/ocrbench/score.py`. Real public pages from the specimen corpus; "
             "ground truth hand-checked in `groundtruth.json`. CPU only (no GPU). `–` = not applicable.", "",
             "| Engine | Family | Pages | " + " | ".join(c[1] for c in cols) + " | s/page | Peak RAM | Licence |",
             "|---|---|---|" + "---|" * len(cols) + "---|---|---|"]
    for e in sorted(engines.values(), key=lambda e: -(e["pair_recall"] or e["table_roi_recall"] or 0)):
        lines.append(
            f"| {e['engine']} | {e['family']} | {e['pages']} | "
            + " | ".join(pct(e[c]) if c != "text_f1" else ("–" if e[c] is None else f"{e[c]:.2f}") for c, _ in cols)
            + f" | {e['sec_per_page'] if e['sec_per_page'] is not None else '–'} | {e['peak_rss_gb']} GB | {e['licence']} |"
        )
    SCORES_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
