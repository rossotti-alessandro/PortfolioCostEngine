"""Run the FeeLens production extractor on every benchmark page, as one more lab engine (SC-5.7).

The app's upload pipeline (``pce.extraction.parsers.extract``, the same function the upload API and the
accuracy protocol's ``baseline`` strategy call) reads each single-page PDF. Its cost facts become the
engine's own fee list, with the evidence box the app would show the analyst, so the lab can put the
app's answer next to the hand-checked figures and the model outputs. Scan copies go through the app's
OCR path because they have no text layer.

Runs in the backend environment, not the bench venv:
    cd backend && uv run python ../data/specimens/ocrbench/app_run.py
Writes var/ocrbench/out/app_baseline/<page_id>.json and _run.json (git-ignored).
"""

from __future__ import annotations

import json
import platform
import resource
import time
from pathlib import Path

from pce.evaluation.gold import FEE_KINDS
from pce.extraction.parsers import extract

ROOT = Path(__file__).resolve().parents[3]
PAGES = ROOT / "var" / "ocrbench" / "pages"
OUT = ROOT / "var" / "ocrbench" / "out" / "app_baseline"
SCALE = 2  # lab boxes are pixels of the 144 dpi render; app evidence is in PDF points


def main() -> None:
    pages = json.loads((Path(__file__).with_name("pages.json")).read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    meta_path = OUT / "_run.json"
    meta: dict = json.loads(meta_path.read_text()) if meta_path.exists() else {"pages": {}}
    for p in pages:
        pdf = PAGES / f"{p['id']}.pdf"
        if (OUT / f"{p['id']}.json").exists() and p["id"] in meta["pages"]:
            continue
        t0 = time.perf_counter()
        err, facts, doc_type = None, [], None
        try:
            res, _ = extract(pdf.name, pdf.read_bytes())
            facts, doc_type = res.facts, res.profile.doc_type.value
        except Exception as e:  # a crash is a result: scored as nothing found
            err = f"{type(e).__name__}: {e}"
        dt = round(time.perf_counter() - t0, 2)
        fees = [
            {
                "label": f.label,
                "value": f.value,
                "b": [v * SCALE for v in f.evidence.bbox] if f.evidence.bbox else None,
                "kind": f.kind,
                "fee_code": f.fee_code,
                "engine": f.evidence.engine,
            }
            for f in facts
            if f.kind in FEE_KINDS and f.value is not None
        ]
        out = {
            "text": "",
            "words": [],
            "regions": [],
            "tables": [],
            "fees": fees,
            "doc_type": doc_type,
            "seconds": dt,
            "includes_load": False,
            "error": err,
        }
        (OUT / f"{p['id']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        meta["pages"][p["id"]] = {"seconds": dt, "includes_load": False, "error": err}
        print(f"app_baseline {p['id']} {dt}s {len(fees)} cost facts {err or ''}", flush=True)
        meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    meta.update(
        engine="app_baseline",
        family="app",
        repo="FeeLens upload pipeline (pce.extraction.parsers.extract)",
        licence="own code",
        machine=f"{platform.machine()} CPU, no GPU",
        peak_rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2),
    )
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
