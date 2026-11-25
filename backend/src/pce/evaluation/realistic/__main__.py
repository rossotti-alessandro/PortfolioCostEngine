"""Run the realistic portfolio benchmark and write a dated report with per-condition gates.

``uv run python -m pce.evaluation.realistic [--n 18] [--variants digital,scan,...] [--workers 4]``
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from . import degrade
from .generate import build
from .score import page_text, score_doc, score_handwritten
from .universe import ROOT

# Proposed thresholds (percent). "min" gates must be reached; "wrong_accepted" is a ceiling on wrong
# values the app shows without a review flag, as a share of values read.
GATES: dict[str, dict[str, float]] = {
    "digital": {"words": 99.5, "figures": 99.5, "holdings": 99.0, "fees": 98.0, "wrong_accepted": 0.5},
    "scan": {"words": 98.0, "figures": 98.0, "holdings": 97.0, "fees": 95.0, "wrong_accepted": 1.0},
    "scan_poor": {"words": 95.0, "figures": 95.0, "holdings": 90.0, "fees": 90.0, "wrong_accepted": 1.0},
    "photo": {"words": 97.0, "figures": 97.0, "holdings": 95.0, "fees": 95.0, "wrong_accepted": 1.0},
    "photo_hard": {"words": 93.0, "figures": 93.0, "holdings": 85.0, "fees": 85.0, "wrong_accepted": 1.0},
    "annotated": {"words": 97.0, "figures": 97.0, "holdings": 97.0, "fees": 95.0, "wrong_accepted": 1.0},
    "handwritten": {"figures": 80.0},
}
PII_GATES = {"detected": 99.0, "damage": 0.0}


def _variant_bytes(variant: str, pdf: bytes, gold: dict, seed: int) -> bytes:
    if variant == "digital":
        return pdf
    if variant in ("scan", "scan_poor"):
        return degrade.scan(pdf, seed, poor=variant == "scan_poor")
    if variant in ("photo", "photo_hard"):
        return degrade.photo(pdf, seed, hard=variant == "photo_hard")
    if variant == "annotated":
        return degrade.annotated(pdf, gold, seed)
    raise ValueError(variant)


def _job(args: tuple[str, str, dict, int, str]) -> dict:
    folder, variant, gold, seed, out = args
    pdf = (Path(folder) / gold["file"]).read_bytes()
    if variant == "handwritten":
        data, figures = degrade.handwritten(gold, seed)
        (Path(out) / f"{Path(gold['file']).stem}-handwritten.pdf").write_bytes(data)
        r = score_handwritten(gold["file"], data, figures)
    else:
        from ...extraction.parsers import extract

        _, digital_pages = extract(gold["file"], pdf)
        data = _variant_bytes(variant, pdf, gold, seed)
        if variant != "digital":
            (Path(out) / f"{Path(gold['file']).stem}-{variant}.pdf").write_bytes(data)
        r = score_doc(gold["file"], data, gold, page_text(digital_pages))
    r.update(variant=variant, layout=gold["layout"])
    return r


def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 2) if b else None


def summarise(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for v in dict.fromkeys(r["variant"] for r in rows):
        rs = [r for r in rows if r["variant"] == v]
        s: dict = {"docs": len(rs), "seconds_per_doc": round(sum(r["seconds"] for r in rs) / len(rs), 1)}
        for k in ("words", "figures", "holdings", "fees", "fee_codes"):
            if all(k in r for r in rs):
                s[k] = _pct(sum(r[k][0] for r in rs), sum(r[k][1] for r in rs))
        if "total_ok" in rs[0]:
            s["total_exact"] = _pct(sum(r["total_ok"] for r in rs), len(rs))
            read = sum(r["facts_read"] for r in rs)
            s["wrong"] = sum(r["wrong"] for r in rs)
            s["wrong_accepted"] = _pct(sum(r["wrong_accepted"] for r in rs), read) or 0.0
            p = [r["pii"] for r in rs]
            s["pii_detected"] = _pct(sum(x["found"] for x in p), sum(x["gold"] for x in p))
            s["pii_misread"] = sum(x["misread"] for x in p)
            s["pii_names_addresses_unmasked"] = sum(x["names_addresses"] for x in p)
            s["mask_damage"] = sum(x["damage"] for x in p)
            kinds: dict[str, list[int]] = {}
            for x in p:
                for k, (a, b) in x["by_kind"].items():
                    kinds.setdefault(k, [0, 0])
                    kinds[k][0] += a
                    kinds[k][1] += b
            s["pii_by_kind"] = {k: _pct(a, b) for k, (a, b) in kinds.items()}
        gate = GATES.get(v, {})
        fails = []
        for k, thr in gate.items():
            got = s.get(k)
            if got is None:
                continue
            if (k == "wrong_accepted" and got > thr) or (k != "wrong_accepted" and got < thr):
                fails.append(f"{k} {got} vs {'≤' if k == 'wrong_accepted' else '≥'}{thr}")
        s["gate"] = "PASS" if not fails else "FAIL: " + "; ".join(fails)
        out[v] = s
    return out


def report(summary: dict, rows: list[dict], stamp: str, n: int) -> str:
    cols = ["words", "figures", "holdings", "total_exact", "fees", "fee_codes", "wrong", "wrong_accepted",
            "pii_detected", "mask_damage", "seconds_per_doc"]  # fmt: skip
    lines = [
        f"# Realistic portfolio benchmark {stamp}",
        "",
        f"{n} SYNTHETIC statements in 6 layouts (CH private EN, CH cantonal DE, Ticino IT, Romandy FR,",
        "Italian bank EUR, US broker USD), real public ISINs, the app's own `extract()`.",
        "Percentages; values exact (no tolerance).",
        "",
        "| condition | " + " | ".join(cols) + " | gate |",
        "|---" * (len(cols) + 2) + "|",
    ]
    for v, s in summary.items():
        lines.append(f"| {v} | " + " | ".join(str(s.get(c, "")) for c in cols) + f" | {s['gate']} |")
    lines += ["", "## Per layout (holdings % / fees %)", "", "| layout | " + " | ".join(summary) + " |",
              "|---" * (len(summary) + 1) + "|"]  # fmt: skip
    for lay in dict.fromkeys(r["layout"] for r in rows):
        cells = []
        for v in summary:
            rs = [r for r in rows if r["layout"] == lay and r["variant"] == v]
            if not rs:
                cells.append("")
            elif "holdings" in rs[0]:
                h = _pct(sum(r["holdings"][0] for r in rs), sum(r["holdings"][1] for r in rs))
                f = _pct(sum(r["fees"][0] for r in rs), sum(r["fees"][1] for r in rs))
                cells.append(f"{h} / {f}")
            else:
                cells.append(str(_pct(sum(r["figures"][0] for r in rs), sum(r["figures"][1] for r in rs))))
        lines.append(f"| {lay} | " + " | ".join(cells) + " |")
    lines += ["", "## Gates", "", "```", json.dumps({"GATES": GATES, "PII": PII_GATES}, indent=1), "```"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=18)
    ap.add_argument("--variants", default=",".join(degrade.VARIANTS))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = a.out or ROOT / "artifacts" / "realistic" / stamp
    docs = out / "documents"
    golds = build(docs, a.n)
    degrade.ensure_fonts()
    jobs = [
        (str(docs), v, g.__dict__, 1000 + i, str(docs))
        for v in a.variants.split(",")
        for i, g in enumerate(golds)
    ]
    with ProcessPoolExecutor(a.workers) as pool:
        rows = list(pool.map(_job, jobs))
    summary = summarise(rows)
    (out / "results.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8"
    )
    (out / "report.md").write_text(report(summary, rows, stamp, a.n), encoding="utf-8")
    print(report(summary, rows, stamp, a.n))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
