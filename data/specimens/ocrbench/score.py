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


BLOCK_PX = 80  # taller than ~3 text lines at 144 dpi


def page_lines(res: dict) -> list[str]:
    """Every line or table row an engine produced, as plain text."""
    lines = [
        ln
        for ln in adapters.strip_markup(res.get("text", "")).splitlines()
        if ln.strip()
    ]
    for t in res.get("tables", []):
        lines += [" | ".join(c or "" for c in row) for row in t["rows"]]
    # A block-level box (paragraph or whole table) counts line by line; as one "line" it would
    # put every label next to every number and inflate the score of block-level engines.
    for w in res.get("words", []):
        b = w.get("b")
        lines += w["t"].splitlines() if b and b[3] - b[1] > BLOCK_PX else [w["t"]]
    lines += visual_rows(res.get("words", []))
    lines += [f"{f['label']} {f['value']}" for f in res.get("fees", [])]
    return lines


def visual_rows_boxes(words: list[dict]) -> list[list[dict]]:
    """Group boxed text into visual rows (same baseline band).

    OCR engines return one box per text run, so a table row's label and value come back as
    separate items. Any pipeline would rebuild rows from the boxes; this is the simplest such step.
    """
    rows: list[list[dict]] = []
    for w in sorted(
        (w for w in words if w.get("b")), key=lambda w: (w["b"][1] + w["b"][3]) / 2
    ):
        cy, h = (w["b"][1] + w["b"][3]) / 2, max(4.0, w["b"][3] - w["b"][1])
        if h > BLOCK_PX:  # a block or table box, not a text line
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


PAIR_WINDOW = 160  # characters of context around the value that may hold its label


def pair_found(lines: list[str], gt: dict, key: str) -> bool:
    """Value and at least half its label words close together on one line or row.

    The window keeps a long paragraph line (block-level engines) from pairing any label
    with any number on it; a table row or printed line is shorter than the window anyway.
    """
    need = fees.label_tokens(gt["label"])
    for ln in lines:
        for m in fees.NUM.finditer(ln):
            if not fees.same_number(key, fees.canon(m.group(1), m.group(2)) or ""):
                continue
            if not need:
                return True
            ctx = ln[max(0, m.start() - PAIR_WINDOW) : m.end() + PAIR_WINDOW // 2]
            if len(need & fees.label_tokens(ctx)) >= max(1, len(need) / 2):
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
    boxes += [
        (f["b"], f"{f['label']} {f['value']}")
        for f in res.get("fees", [])
        if f.get("b")
    ]
    boxes += [
        (r["b"], r.get("text", "")) for r in res.get("regions", []) if r.get("text")
    ]
    regions = res.get("regions", [])
    table_regs = [
        r["b"] for r in regions if "table" in r["label"].lower() or r["label"] == "otsl"
    ]
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
        el = g.get("element", "table" if g.get("in_table") else "text")
        c[f"gt_el:{el}"] += 1
        c[f"pair_el:{el}"] += p
        if g.get("in_table"):
            c["gt_table"] += 1
            c["table_pair"] += p
        if g.get("bbox"):
            c["gt_boxed"] += 1
            x0, y0, x1, y1 = (v * S for v in g["bbox"])
            ctr, h = ((x0 + x1) / 2, (y0 + y1) / 2), (y1 - y0)
            hits = [
                b for b, t in boxes if b and centre_in(b, ctr) and has_number(t, key)
            ]
            f["l"] = bool(hits)
            f["t"] = any((b[3] - b[1]) <= 3.5 * max(h, 8) for b in hits)
            c["located"] += f["l"]
            c["located_tight"] += f["t"]
            c["roi"] += any(centre_in(r["b"], ctr) for r in regions)
            # Which region label holds the fee (smallest region wins): tells us what to detect.
            holders = sorted(
                (r for r in regions if centre_in(r["b"], ctr)),
                key=lambda r: (r["b"][2] - r["b"][0]) * (r["b"][3] - r["b"][1]),
            )
            if regions:
                c[
                    f"rl:{el}:{holders[0]['label'].lower() if holders else '(none)'}"
                ] += 1
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
        preds2 = preds + [
            i["value"]
            for i in fees.extract_fee_tables(
                res.get("tables", []), res.get("text", "")[:3000]
            )
        ]
    tp, npred = match(preds, gt_keys)
    tp2, npred2 = match(preds2, gt_keys)
    c["pred"] += npred
    c["tp"] += tp
    c["pred2"] += npred2
    c["tp2"] += tp2
    c["gt_distinct"] += len(gt_keys)
    # structure: the fee's value and label in one row of an engine-produced table
    trows = [
        " | ".join(c_ or "" for c_ in row)
        for t in res.get("tables", [])
        for row in t["rows"]
    ]
    for g, f in zip(
        [g for g in gt_items if fees.value_key(g["value"])], [f for f in flags if f]
    ):
        if g.get("in_table"):
            f["s"] = pair_found(trows, g, fees.value_key(g["value"]))
            c["table_struct"] += f["s"]
    out = dict(c)
    if ref_text is not None:
        out["text_f1"] = round(
            f1(
                tokens(adapters.strip_markup(res.get("text", "")) or full),
                tokens(ref_text),
            ),
            3,
        )
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
            ref[pid] = (
                json.loads((OUT / "pdfplumber" / f"{pid}.json").read_text())["text"]
                if (OUT / "pdfplumber" / f"{pid}.json").exists()
                else None
            )
    per_page: dict[str, dict] = {}
    runs: dict[
        str, dict
    ] = {}  # engine -> {meta, pages: {pid: (score, seconds or None, error)}}
    for d in sorted(OUT.iterdir()):
        if not d.is_dir() or not (d / "_run.json").exists():
            continue
        run = runs[d.name] = {
            "meta": json.loads((d / "_run.json").read_text()),
            "pages": {},
        }
        for pid, p in pages.items():
            f = d / f"{pid}.json"
            gt_key = p.get("gt_from", pid)
            if not f.exists() or gt_key not in gt:
                continue
            res = json.loads(f.read_text())
            s = score_page(res, gt[gt_key]["items"], ref.get(pid))
            per_page.setdefault(pid, {})[d.name] = s
            run["pages"][pid] = (
                s,
                None if res.get("includes_load") else res["seconds"],
                bool(res.get("error")),
            )
    sets = json.loads((HERE / "vlm_core.json").read_text(encoding="utf-8"))
    core, mini = set(sets["pages"]), set(sets["mini"])
    engines = {k: e for k, r in runs.items() if (e := summarise(k, r, None))}

    def same_pages(only: set[str]) -> dict:
        # a fair table holds only engines that ran every page of the set
        return {k: e for k, r in runs.items() if (e := summarise(k, r, only)) and e["pages"] == len(only)}

    engines_core, engines_mini = same_pages(core), same_pages(mini)
    families = family_scores(runs, pages)
    SCORES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCORES_JSON.write_text(
        json.dumps(
            {
                "engines": engines,
                "engines_core": engines_core,
                "engines_mini": engines_mini,
                "families": families,
                "per_page": per_page,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    write_md(engines, engines_core, len(core), families, engines_mini, len(mini))
    print(SCORES_MD.read_text(encoding="utf-8"))


def family(p: dict) -> str:
    """Document family of a page: its stratum without the language suffix."""
    return re.sub(r" (EN|DE|FR|IT)$", "", p["stratum"])


def family_scores(runs: dict, pages: dict) -> dict:
    """Label+value pair recall per engine and document family, with the pages and figures behind it."""
    out: dict[str, dict] = {}
    for name, run in runs.items():
        if run["meta"].get("family") == "layout":  # regions only, no text to pair
            continue
        tot: dict[str, Counter] = {}
        for pid, (s, _sec, _err) in run["pages"].items():
            t = tot.setdefault(family(pages[pid]), Counter())
            t["pages"] += 1
            t["gt"] += s.get("gt", 0)
            t["pair"] += s.get("pair", 0)
        rows = {
            f: {
                "pages": t["pages"],
                "gt": t["gt"],
                "pair_recall": ratio(t["pair"], t["gt"]),
            }
            for f, t in sorted(tot.items())
            if t["gt"]
        }
        if rows and any(r["pair_recall"] is not None for r in rows.values()):
            out[name] = rows
    return out


def summarise(name: str, run: dict, only: set[str] | None) -> dict | None:
    """Totals over the pages this engine ran (optionally only those in `only`). Unrun pages are left out."""
    meta = run["meta"]
    tot: Counter = Counter()
    f1s, secs, errors = [], [], 0
    for pid, (s, sec, err) in run["pages"].items():
        if only is not None and pid not in only:
            continue
        errors += err
        if "text_f1" in s and name != "pdfplumber":
            f1s.append(s["text_f1"])
        for k, v in s.items():
            if k not in ("text_f1", "items"):
                tot[k] += v
        if sec is not None:
            secs.append(sec)
        tot["pages"] += 1
    if not tot["pages"]:
        return None
    return {
        "engine": name,
        "family": meta.get("family"),
        "repo": meta.get("repo"),
        "licence": meta.get("licence"),
        "pages": tot["pages"],
        "errors": errors,
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
        "element_pair_recall": {
            k[6:]: ratio(tot["pair_el:" + k[6:]], v)
            for k, v in sorted(tot.items())
            if k.startswith("gt_el:")
        },
        "region_labels": {
            k[3:]: v for k, v in sorted(tot.items()) if k.startswith("rl:")
        }
        or None,
    }


def pct(v: float | None) -> str:
    return "–" if v is None else f"{v * 100:.0f}%"


def write_md(
    engines: dict, engines_core: dict, n_core: int, families: dict, engines_mini: dict, n_mini: int
) -> None:
    lines = [
        "# Local OCR / layout / VLM benchmark — scores",
        "",
        "Generated by `data/specimens/ocrbench/score.py`. Real public pages from the specimen corpus; "
        "ground truth hand-checked in `groundtruth.json`. CPU only (no GPU). `–` = not applicable.",
        "",
        f"## Same {n_core} pages for every engine (fair comparison)",
        "",
        *table(engines_core),
        "",
        f"## Same {n_mini} hard pages (slow VLM triage set, one model at a time)",
        "",
        *table(engines_mini),
        "",
        f"## Every page each engine ran (fast engines: all {max(e['pages'] for e in engines.values())})",
        "",
        *table(engines),
        "",
        "## Label+value same row, by layout element (every page each engine ran)",
        "",
        *element_table(engines),
        "",
        "## Label+value same row, by document family",
        "",
        *family_table(families),
    ]
    SCORES_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


ELEMENTS = ("table", "key_value", "text", "footnote")


def element_table(engines: dict) -> list[str]:
    lines = [
        "| Engine | Pages | " + " | ".join(ELEMENTS) + " |",
        "|---|---|" + "---|" * len(ELEMENTS),
    ]
    for e in sorted(engines.values(), key=lambda e: -(e["pair_recall"] or 0)):
        if e["family"] == "layout":
            continue
        el = e["element_pair_recall"]
        lines.append(
            f"| {e['engine']} | {e['pages']} | "
            + " | ".join(pct(el.get(k)) for k in ELEMENTS)
            + " |"
        )
    return lines


def family_table(families: dict) -> list[str]:
    fams = sorted({f for rows in families.values() for f in rows})
    lines = ["| Engine | " + " | ".join(fams) + " |", "|---|" + "---|" * len(fams)]
    for name, rows in sorted(families.items()):
        lines.append(
            f"| {name} | "
            + " | ".join(
                pct(rows[f]["pair_recall"]) + f" ({rows[f]['pages']})"
                if f in rows
                else "–"
                for f in fams
            )
            + " |"
        )
    return lines


def table(engines: dict) -> list[str]:
    cols = [
        ("value_recall", "Values read"),
        ("pair_recall", "Label+value same row"),
        ("table_struct_recall", "In a table row"),
        ("located_tight", "Value boxed (tight)"),
        ("table_roi_recall", "Table ROI hit"),
        ("extract_precision", "Extract precision"),
        ("extract_recall", "Extract recall"),
        ("extract2_precision", "Table-aware precision"),
        ("extract2_recall", "Table-aware recall"),
        ("text_f1", "Text F1"),
    ]
    lines = [
        "| Engine | Family | Pages | "
        + " | ".join(c[1] for c in cols)
        + " | s/page | Peak RAM | Licence |",
        "|---|---|---|" + "---|" * len(cols) + "---|---|---|",
    ]
    for e in sorted(
        engines.values(),
        key=lambda e: -(e["pair_recall"] or e["table_roi_recall"] or 0),
    ):
        ram = (
            f"{e['peak_rss_gb']} GB" if e["peak_rss_gb"] is not None else "sum of parts"
        )
        lines.append(
            f"| {e['engine']} | {e['family']} | {e['pages']} | "
            + " | ".join(
                pct(e[c])
                if c != "text_f1"
                else ("–" if e[c] is None else f"{e[c]:.2f}")
                for c, _ in cols
            )
            + f" | {e['sec_per_page'] if e['sec_per_page'] is not None else '–'} | {ram} | {e['licence']} |"
        )
    return lines


if __name__ == "__main__":
    main()
