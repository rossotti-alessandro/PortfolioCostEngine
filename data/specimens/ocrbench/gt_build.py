"""Build groundtruth.json from the hand-checked groundtruth.txt (SC-5.6).

Adds each value's box from the PDF text layer: the pdfplumber word(s) holding the same
number, preferring the line that shares the most label words, then reading order, each
word used once. Pages whose text layer differs from the printed page, and image-only
pages, get no boxes (bbox null), never a guessed one.

Usage: python data/specimens/ocrbench/gt_build.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
import fees  # noqa: E402

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
PAGES = ROOT / "var" / "ocrbench" / "pages"
NO_BOX = {"tariff-bcv-clientele-privee-fr-p12"}  # text layer differs from the printed page


def parse(txt: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    cur = None
    for ln in txt.splitlines():
        if ln.startswith("## "):
            cur = ln[3:].strip()
            out[cur] = []
        elif cur and ln[:2] in ("T|", "N|"):
            kind, label, value = ln.split("|", 2)
            out[cur].append({"label": label.strip(), "value": value.strip(), "in_table": kind == "T"})
    return out


def main() -> None:
    gt = parse((HERE / "groundtruth.txt").read_text(encoding="utf-8"))
    meta = {p["id"]: p for p in json.loads((HERE / "pages.json").read_text(encoding="utf-8"))}
    missing = set(k for k, p in meta.items() if p["variant"] == "original") - set(gt)
    if missing:
        print("pages without ground truth:", sorted(missing))
    boxed = total = 0
    for pid, items in gt.items():
        p = meta[pid]
        if not p["text_layer"] or pid in NO_BOX:
            for it in items:
                it["bbox"] = None
            total += len(items)
            continue
        with pdfplumber.open(PAGES / f"{pid}.pdf") as pdf:
            words = pdf.pages[0].extract_words()
        lines: dict[int, list] = {}
        for i, w in enumerate(words):
            lines.setdefault(round(w["top"] / 3), []).append(i)
        line_of = {i: k for k, idx in lines.items() for i in idx}
        line_tokens = {k: fees.label_tokens(" ".join(words[i]["text"] for i in idx)) for k, idx in lines.items()}
        used: set[int] = set()
        for it in items:
            total += 1
            key = fees.value_key(it["value"])
            need = fees.label_tokens(it["label"])
            cands = []
            for i, w in enumerate(words):
                if i in used or not any(fees.same_number(key, n) for n in fees.numbers(w["text"])):
                    continue
                # a number split over words ("1 767") is matched on its last word
                cands.append((-len(need & line_tokens[line_of[i]]), w["top"], w["x0"], i))
            if not cands and key:
                for k, idx in lines.items():  # number split over several words
                    txt = " ".join(words[i]["text"] for i in idx)
                    if any(fees.same_number(key, n) for n in fees.numbers(txt)):
                        hits = [i for i in idx if any(c.isdigit() for c in words[i]["text"]) and i not in used]
                        if hits:
                            cands.append((-len(need & line_tokens[k]), words[hits[-1]]["top"], 0, hits[-1]))
            if cands:
                i = sorted(cands)[0][3]
                used.add(i)
                w = words[i]
                it["bbox"] = [round(w["x0"], 1), round(w["top"], 1), round(w["x1"], 1), round(w["bottom"], 1)]
                boxed += 1
            else:
                it["bbox"] = None
                print(f"no box: {pid} | {it['label']} | {it['value']}")
    out = {
        "about": "Hand-checked fee figures per benchmark page. bbox: PDF points, top-left origin, from the "
                 "text layer; null when the page has no trustworthy text layer. See groundtruth.txt for rules.",
        "pages": {pid: {"items": items} for pid, items in gt.items()},
    }
    (HERE / "groundtruth.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(gt)} pages, {total} fee figures, {boxed} with a box")


if __name__ == "__main__":
    main()
