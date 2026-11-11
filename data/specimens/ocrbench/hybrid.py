"""Hybrid pipelines built from the engines' stored outputs, scored like any engine (SC-5.6).

No new model calls: each hybrid recombines what run.py already stored, so its cost is the
sum of its parts (reported as such).

hybrid_route   per page: text layer (pdfplumber words) when the page has one, else the OCR
               engine's lines; a layout model's table regions; words re-assembled into table
               rows inside each region. The cheap path every page takes.
hybrid_vlm     hybrid_route, plus the VLM's output for pages without a text layer or with a
               table region (the slow path only where it helps).
consensus      not an engine: compares the cheap path's fee numbers with the VLM's. Numbers
               both agree on are accepted; the rest go to review (agent or analyst). Written to
               var/ocrbench/consensus.json.

Usage: python data/specimens/ocrbench/hybrid.py [--ocr rapidocr] [--layout heron] [--vlm paddleocr_vl]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fees  # noqa: E402
import score  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE.parents[2] / "var" / "ocrbench" / "out"


def load(engine: str, pid: str) -> dict | None:
    f = OUT / engine / f"{pid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def words_of(engine: str, pid: str) -> list[dict]:
    r = load(engine, pid)
    return r["words"] if r else []


def rows_in(box: list[float], words: list[dict]) -> list[list[str]]:
    """Visual rows of the words whose centre lies in box, each row split into cells by gaps."""
    inside = [w for w in words if box[0] - 4 <= (w["b"][0] + w["b"][2]) / 2 <= box[2] + 4
              and box[1] - 4 <= (w["b"][1] + w["b"][3]) / 2 <= box[3] + 4]
    rows = []
    for line in score.visual_rows_boxes(inside):
        cells, last_x1 = [], None
        for w in sorted(line, key=lambda w: w["b"][0]):
            h = w["b"][3] - w["b"][1]
            if last_x1 is not None and w["b"][0] - last_x1 < 1.2 * h:
                cells[-1] += " " + w["t"]
            else:
                cells.append(w["t"])
            last_x1 = w["b"][2]
        rows.append(cells)
    return rows


def route(p: dict, ocr: str, layout: str) -> tuple[dict, float]:
    pid = p["id"]
    if p["text_layer"]:
        base = load("pdfplumber", pid)
        words = base["words"] if base else []
        sec = base["seconds"] if base else 0
        # word-level boxes from the text layer for clean cells
        from run import text_layer_words  # noqa: PLC0415

        cell_words = text_layer_words(HERE.parents[2] / "var" / "ocrbench" / "pages" / f"{pid}.pdf")
    else:
        base = load(ocr, pid)
        words = base["words"] if base else []
        cell_words = words
        sec = base["seconds"] if base else 0
    lay = load(layout, pid) or {"regions": [], "seconds": 0}
    sec += lay["seconds"]
    regions = lay["regions"]
    tables = [{"b": r["b"], "rows": rows_in(r["b"], cell_words)} for r in regions if "table" in r["label"].lower()]
    text = "\n".join(score.visual_rows(words))
    return {"text": text, "words": words, "regions": regions, "tables": tables, "fees": []}, sec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", default="rapidocr")
    ap.add_argument("--layout", default="heron")
    ap.add_argument("--vlm", default="paddleocr_vl")
    a = ap.parse_args()
    pages = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
    gt = json.loads((HERE / "groundtruth.json").read_text(encoding="utf-8"))["pages"]
    names = {"hybrid_route": f"text layer or {a.ocr} + {a.layout} tables",
             "hybrid_vlm": f"hybrid_route + {a.vlm} on scans and table pages"}
    consensus = {"accepted": 0, "accepted_correct": 0, "review": 0, "review_correct": 0, "gt": 0,
                 "found_by_union": 0, "pages": 0, "vlm": a.vlm}
    for name in names:
        (OUT / name).mkdir(parents=True, exist_ok=True)
    meta = {k: {"engine": k, "family": "hybrid", "repo": v, "licence": "per component", "pages": {}}
            for k, v in names.items()}
    for p in pages:
        res, sec = route(p, a.ocr, a.layout)
        res.update(seconds=round(sec, 2), includes_load=False, error=None)
        (OUT / "hybrid_route" / f"{p['id']}.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        meta["hybrid_route"]["pages"][p["id"]] = {"seconds": res["seconds"]}
        v = load(a.vlm, p["id"])
        use_vlm = v is not None and (not p["text_layer"] or res["tables"])
        h = dict(res)
        if use_vlm:
            h = {**res, "text": res["text"] + "\n" + v.get("text", ""), "words": res["words"] + v.get("words", []),
                 "tables": res["tables"] + v.get("tables", []), "seconds": round(sec + v["seconds"], 2)}
        (OUT / "hybrid_vlm" / f"{p['id']}.json").write_text(json.dumps(h, ensure_ascii=False), encoding="utf-8")
        meta["hybrid_vlm"]["pages"][p["id"]] = {"seconds": h["seconds"]}
        # consensus between the cheap path and the VLM, on pages the VLM ran
        if v is None:
            continue
        g = gt.get(p.get("gt_from", p["id"]), {}).get("items", [])
        keys = [k for k in (fees.value_key(x["value"]) for x in g) if k]
        cheap = {i["value"] for i in fees.extract_fee_lines("\n".join(score.page_lines(res)))}
        vlm = {i["value"] for i in fees.extract_fee_lines("\n".join(score.page_lines(v)))}
        agreed = {x for x in cheap if any(fees.same_number(x, y) for y in vlm)}
        review = (cheap | vlm) - agreed
        is_gt = lambda x: any(fees.same_number(k, x) for k in keys)  # noqa: E731
        consensus["pages"] += 1
        consensus["gt"] += len(set(keys))
        consensus["accepted"] += len(agreed)
        consensus["accepted_correct"] += sum(map(is_gt, agreed))
        consensus["review"] += len(review)
        consensus["review_correct"] += sum(map(is_gt, review))
        consensus["found_by_union"] += sum(1 for k in set(keys) if any(fees.same_number(k, x) for x in cheap | vlm))
    for k, m in meta.items():
        (OUT / k / "_run.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    (OUT.parent / "consensus.json").write_text(json.dumps(consensus, indent=1), encoding="utf-8")
    print(json.dumps(consensus, indent=1))


if __name__ == "__main__":
    main()
