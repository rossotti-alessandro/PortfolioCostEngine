"""Draft ground-truth fee items from the PDF text layer, for a human to check (SC-5.6).

For each born-digital benchmark page it lists every number printed on a line that has a
fee word, with the label (the line without its numbers) and the number's box from the
pdfplumber words. A person then deletes what is not a fee, fixes labels, adds missed
items and marks in_table, and saves the result as groundtruth.json. The draft is never
used for scoring as is.

Usage: python data/specimens/ocrbench/gt_propose.py > var/ocrbench/gt_draft.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
import fees  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
PAGES = ROOT / "var" / "ocrbench" / "pages"


def main() -> None:
    pages = json.loads(Path(__file__).with_name("pages.json").read_text(encoding="utf-8"))
    draft = {}
    for p in pages:
        if p["variant"] != "original" or not p["text_layer"]:
            continue
        with pdfplumber.open(PAGES / f"{p['id']}.pdf") as pdf:
            pg = pdf.pages[0]
            words = pg.extract_words()
            tables = [t.bbox for t in pg.find_tables()]
            rows: dict[int, list] = {}
            for w in words:
                rows.setdefault(round(w["top"] / 3), []).append(w)
            items = []
            for ws in rows.values():
                ws.sort(key=lambda w: w["x0"])
                line = " ".join(w["text"] for w in ws)
                if not fees.FEE_WORDS.search(line):
                    continue
                for w in ws:
                    m = fees.NUM.search(w["text"])
                    if not m or re.fullmatch(r"(19|20)\d\d", m.group(1)):
                        continue
                    label = re.sub(r"\s+", " ", fees.NUM.sub(" ", line)).strip(" :;-–|")
                    box = [round(w["x0"], 1), round(w["top"], 1), round(w["x1"], 1), round(w["bottom"], 1)]
                    in_table = any(t[0] <= w["x0"] and w["x1"] <= t[2] and t[1] <= w["top"] and w["bottom"] <= t[3]
                                   for t in tables)
                    items.append({"label": label[:120], "value": w["text"], "bbox": box, "in_table": in_table,
                                  "line": line[:200]})
            draft[p["id"]] = {"file": p["file"], "page": p["page"], "items": items}
    print(json.dumps(draft, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
