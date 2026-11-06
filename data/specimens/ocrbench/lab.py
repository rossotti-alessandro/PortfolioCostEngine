"""Build the OCR Lab: a static viewer of every engine's output over every benchmark page (SC-5.6).

Writes var/ocrbench/lab/ (git-ignored, holds page images of third-party documents):
    index.html   from lab_template.html
    data.json    pages, ground truth, per-engine outputs and scores, engine summary
    img/<page>.jpg

Usage: python data/specimens/ocrbench/lab.py   (after run.py and score.py)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
OCR = ROOT / "var" / "ocrbench"
LAB = OCR / "lab"
JPEG_SCALE = 0.75  # of the 144 dpi render: ~108 dpi, enough to read the page in the viewer


def r1(b):
    return [round(v, 1) for v in b] if b else None


def main() -> None:
    pages = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
    gt = json.loads((HERE / "groundtruth.json").read_text(encoding="utf-8"))["pages"]
    scores = json.loads((OCR / "scores.json").read_text(encoding="utf-8"))
    meta_extra = json.loads((HERE / "models.json").read_text(encoding="utf-8"))
    if LAB.exists():
        shutil.rmtree(LAB)
    (LAB / "img").mkdir(parents=True)
    out_pages = []
    outputs: dict[str, dict] = {}
    for p in pages:
        img = Image.open(OCR / "pages" / f"{p['id']}.png").convert("RGB")
        W, H = img.size
        img.resize((int(W * JPEG_SCALE), int(H * JPEG_SCALE)), Image.LANCZOS).save(
            LAB / "img" / f"{p['id']}.jpg", "JPEG", quality=72, optimize=True)
        gkey = p.get("gt_from", p["id"])
        items = gt.get(gkey, {}).get("items", [])
        if p["variant"] == "scan-sim":  # boxes of the original page still mark the right spot
            pass
        out_pages.append({
            **{k: p[k] for k in ("id", "file", "page", "stratum", "document_type", "language", "issuer", "variant",
                                 "text_layer")},
            "w": W, "h": H,
            "gt": [{"label": g["label"], "value": g["value"], "in_table": g["in_table"],
                    "b": [v * 2 for v in g["bbox"]] if g.get("bbox") else None} for g in items],
            "scores": scores["per_page"].get(p["id"], {}),
        })
        for d in sorted((OCR / "out").iterdir()):
            f = d / f"{p['id']}.json"
            if not f.exists():
                continue
            r = json.loads(f.read_text(encoding="utf-8"))
            outputs.setdefault(d.name, {})[p["id"]] = {
                "words": [[w["t"][:300], r1(w["b"])] for w in r.get("words", [])[:1500]],
                "regions": [[x["label"], r1(x["b"]), x.get("s")] for x in r.get("regions", [])[:400]],
                "tables": [{"b": r1(t.get("b")), "rows": [[(c or "")[:120] for c in row] for row in t["rows"][:80]]}
                           for t in r.get("tables", [])[:12]],
                "fees": [[x["label"][:120], x["value"][:60], r1(x.get("b"))] for x in r.get("fees", [])],
                "text": (r.get("text") or "")[:6000],
                "sec": r.get("seconds"),
                "err": r.get("error"),
            }
    engines = scores["engines"]
    for k, e in engines.items():
        e.update(meta_extra.get(k, {}))
    data = {"pages": out_pages, "engines": engines, "outputs": outputs, "models": meta_extra}
    (LAB / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    shutil.copy(HERE / "lab_template.html", LAB / "index.html")
    size = sum(f.stat().st_size for f in LAB.rglob("*") if f.is_file())
    print(f"lab -> {LAB} ({size / 1e6:.1f} MB, {len(out_pages)} pages, {len(outputs)} engines)")


if __name__ == "__main__":
    main()
