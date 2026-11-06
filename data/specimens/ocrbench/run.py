"""Run one engine over the benchmark pages and store its raw outputs (SC-5.6).

One process per engine, so peak memory (ru_maxrss) is that engine's own.
Outputs are git-ignored: var/ocrbench/out/<engine>/<page_id>.json plus _run.json
with load time, per-page seconds, peak RSS, CPU and library versions.

Usage (bench venv):
    python data/specimens/ocrbench/run.py <engine> [--only page_id ...] [--limit N]
Engines: see adapters.MODELS.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import sys
import time
import traceback
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import adapters  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
PAGES = ROOT / "var" / "ocrbench" / "pages"
OUT = ROOT / "var" / "ocrbench" / "out"
PAGES_JSON = Path(__file__).with_name("pages.json")


def text_layer_words(pdf: Path) -> list[dict]:
    """Born-digital words in image pixels, for pipelines that read the PDF text layer (TATR)."""
    import pdfplumber

    with pdfplumber.open(pdf) as doc:
        return [
            {"t": w["text"], "b": [w["x0"] * adapters.SCALE, w["top"] * adapters.SCALE,
                                   w["x1"] * adapters.SCALE, w["bottom"] * adapters.SCALE], "c": 1.0}
            for w in doc.pages[0].extract_words()
        ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=sorted(adapters.MODELS))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--core", action="store_true", help="only the VLM core subset (vlm_core.json)")
    ap.add_argument("--force", action="store_true", help="re-run pages that already have output")
    a = ap.parse_args()

    pages = json.loads(PAGES_JSON.read_text(encoding="utf-8"))
    if a.only:
        pages = [p for p in pages if p["id"] in a.only]
    if a.core:
        core = json.loads(PAGES_JSON.with_name("vlm_core.json").read_text(encoding="utf-8"))["pages"]
        pages = [p for p in pages if p["id"] in core]
    if a.limit:
        pages = pages[: a.limit]
    out_dir = OUT / a.engine
    out_dir.mkdir(parents=True, exist_ok=True)
    fn = adapters.RUNNERS[a.engine]
    run_meta_path = out_dir / "_run.json"
    meta = json.loads(run_meta_path.read_text()) if run_meta_path.exists() else {"pages": {}}
    meta.update({
        "engine": a.engine, **{k: v for k, v in adapters.MODELS[a.engine].items() if k != "fn"},
        "machine": f"{platform.processor() or platform.machine()} x{__import__('os').cpu_count()} CPU, no GPU",
        "python": platform.python_version(),
    })
    try:
        import torch
        import transformers

        meta["torch"], meta["transformers"] = torch.__version__, transformers.__version__
    except ImportError:
        pass

    first = True
    for p in pages:
        dest = out_dir / f"{p['id']}.json"
        if dest.exists() and not a.force:
            continue
        img = Image.open(PAGES / f"{p['id']}.png")
        pdf = PAGES / f"{p['id']}.pdf"
        words = text_layer_words(pdf) if p["text_layer"] else None
        t0 = time.perf_counter()
        try:
            res = fn(img, pdf_page=str(pdf), words=words)
            err = None
        except Exception as e:  # one bad page must not stop the run; the error is scored as a miss
            res, err = adapters.empty(), f"{type(e).__name__}: {e}"
            traceback.print_exc()
        dt = time.perf_counter() - t0
        res["error"] = err
        res["seconds"] = round(dt, 2)
        res["includes_load"] = first
        dest.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        meta["pages"][p["id"]] = {"seconds": round(dt, 2), "includes_load": first, "error": err}
        first = False
        meta["peak_rss_gb"] = max(meta.get("peak_rss_gb", 0),
                                  round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2))
        run_meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(f"{a.engine} {p['id']} {dt:.1f}s {'ERR ' + err if err else ''}", flush=True)


if __name__ == "__main__":
    main()
