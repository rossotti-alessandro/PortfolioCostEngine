"""Workflow arena (SC-5.10): score complete extraction workflows side by side on the same pages.

Each workflow turns a page into fee facts (label, value, page box, review flag). They are scored with the
same rules as the extraction-strategy harness (``data/specimens/strategies/score.py``, SC-5.8), on every
hand-checked page of the model lab (``data/specimens/ocrbench/groundtruth.json``):

    app before SC-5.8      the app's type parsers alone
    app after SC-5.8       parsers + finder, cross-checked and verified (``parsers.extract``)
    finder + verify        the finder on the text layer, values re-read by Tesseract on their crops
    finder + layout        the same, with table regions from PP-DocLayoutV3, verified by RapidOCR
    vision reader          PaddleOCR-VL table rows, each value anchored to a text-layer box
    agentic                finder + verify, then a local language model reviews every candidate (agent.py)

The harness dumps each workflow's predictions to ``var/strategies/<name>.json`` (run it first); the
agent writes ``var/arena/agent/``. This script scores them all, per page and per figure, and writes
``var/arena/arena.json`` (read by the lab) and ``RESULTS.md``.

Runs in the backend environment of a checkout that has the finder (PR #15):
    cd var/arena/wt/backend && uv run python ../../../../data/specimens/arena/run.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WT = ROOT / "var" / "arena" / "wt"
sys.path.insert(0, str(WT / "data" / "specimens" / "strategies"))
sys.path.insert(0, str(HERE))
import score  # noqa: E402  (the harness scorer, read-only)
from agent import flag_only  # noqa: E402

DUMPS = WT / "var" / "strategies"
BENCH = ROOT / "data" / "specimens" / "ocrbench"
WORKFLOWS = [  # (key, name, harness dump, how it works)
    ("app_before", "App before SC-5.8", "rules (parsers before SC-5.8)",
     "The app's per-document-type parsers. Precise where they know the layout, blind elsewhere."),
    ("app_after", "App after SC-5.8", "production extract() after SC-5.8",
     "Parsers plus the layout-aware finder, cross-checked; doubtful values go to review."),
    ("finder_verify", "Finder + verify", "finder @text + verify(tesseract crops)",
     "Every figure on the page linked to its row label and column header; Tesseract re-reads each value."),
    ("finder_layout", "Finder + table layout", "finder @text + ppdoclayout3 + verify(rapidocr)",
     "As above, with table regions from PP-DocLayoutV3; RapidOCR re-reads each value."),
    ("vision", "Vision reader", "vlm-anchored paddleocr_vl",
     "PaddleOCR-VL reads table rows; each value is anchored to a text-layer box (no box, no figure)."),
]  # fmt: skip
OUT = ROOT / "var" / "arena"
AGENT_HOW = ("Finder + verify, then a local language model checks each candidate with tools (second OCR, "
             "table row) and keeps, drops or flags it. It cannot write a number.")  # fmt: skip
FLAG_HOW = ("The same agent run, but a 'not a fee' answer only sends the figure to review instead of dropping it: "
            "the model can never remove a figure on its own.")  # fmt: skip
for d in sorted((OUT / "agent").glob("*/")):  # one agentic workflow per local model run with agent.py --model
    WORKFLOWS.append((f"agentic:{d.name}", f"Agentic review ({d.name})", f"agent:{d.name}", AGENT_HOW))
    WORKFLOWS.append(
        (f"agentic_flag:{d.name}", f"Agent flags only ({d.name})", f"agentflag:{d.name}", FLAG_HOW)
    )


def predictions() -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = {}
    for key, _, dump, _ in WORKFLOWS:
        if dump.startswith("agent:"):
            runs = (OUT / "agent" / dump[6:]).glob("*.json")
            out[key] = {f.stem: json.loads(f.read_text(encoding="utf-8"))["preds"] for f in runs}
        elif dump.startswith("agentflag:"):
            cands = json.loads(
                (DUMPS / "finder @text + verify(tesseract crops).json").read_text(encoding="utf-8")
            )
            runs = (OUT / "agent" / dump[10:]).glob("*.json")
            out[key] = {
                f.stem: flag_only(cands[f.stem], json.loads(f.read_text(encoding="utf-8"))["log"])
                for f in runs
            }
        elif (f := DUMPS / f"{dump}.json").exists():
            out[key] = json.loads(f.read_text(encoding="utf-8"))
    return out


def seconds() -> dict[str, dict[str, float]]:
    """Seconds per page as the harness measured them; the agent adds its own model time on top."""
    prev = json.loads((DUMPS / "scores.json").read_text(encoding="utf-8"))
    secs: dict[str, dict[str, float]] = {}
    for key, _, dump, _ in WORKFLOWS:
        if run := prev.get(f"{dump}@all"):
            secs[key] = {"median": run["summary"]["s_per_page"]}
        elif dump.startswith("agent") and "finder_verify" in secs:  # the agent runs after finder + verify
            run_dir = OUT / "agent" / dump.partition(":")[2]
            agent = [json.loads(f.read_text())["seconds"] for f in run_dir.glob("*.json")]
            if agent:
                secs[key] = {"median": round(secs["finder_verify"]["median"] + statistics.median(agent), 2)}
    return secs


def figure_hits(gold: list[dict], preds: list[dict]) -> list[str]:
    """Per gold figure: found (same value, label matches), review (found but flagged), or missed.
    The same one-to-one greedy matching as ``score.score_page``."""
    gv = [score.gold_value(g["value"]) for g in gold]
    pv = [Decimal(p["value"]) if p.get("value") not in (None, "") else None for p in preds]
    used: set[int] = set()
    res = ["missed"] * len(gold)
    for pi, p in enumerate(preds):
        text = f"{p.get('label', '')} {p.get('snippet', '')}"
        for gi, g in enumerate(gold):
            if gi not in used and score.same_value(gv[gi], pv[pi]) and score.label_ok(g["label"], text):
                used.add(gi)
                res[gi] = "review" if p.get("needs_review") else "found"
                break
    return res


def portfolio(specs: list[str]) -> list[dict] | None:
    """Whole-prospect results of the accuracy protocol (``python -m pce.evaluation`` results.json), one per
    workflow that runs inside the app: "<workflow name>=<path to results.json>"."""
    from pce.evaluation import gold  # noqa: PLC0415  (backend env; only needed with --portfolio)

    pinned = {
        c: len(getattr(gold, c.replace("-", "_"))(OUT).portfolio.expect)
        for c in ("synthetic-p1042", "synthetic-p2077")
    }
    rows = []
    for spec in specs:
        name, _, path = spec.partition("=")
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if not r["corpus"].startswith("synthetic"):
                continue
            n = pinned[r["corpus"]]
            rows.append({"workflow": name, "corpus": r["corpus"], "variant": r["variant"], "recall": r["recall"],
                         "totals": n, "totals_ok": max(0, n - r["portfolio_mismatches"]), "silent_error": r["silent_error"]})  # fmt: skip
    return rows or None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--portfolio", nargs="*", default=[], help='"<workflow>=<results.json>" from pce.evaluation'
    )
    args = ap.parse_args()
    pages = json.loads((BENCH / "pages.json").read_text(encoding="utf-8"))
    gold = json.loads((BENCH / "groundtruth.json").read_text(encoding="utf-8"))["pages"]
    preds = predictions()
    secs = seconds()
    # Fair comparison: only pages every present workflow covered (the vision reader ran on the core set).
    ids = [p["id"] for p in pages if (p.get("gt_from") or p["id"]) in gold]
    common = [i for i in ids if all(i in preds[k] for k in preds)]
    table, per_page = {}, {}
    for key, name, _, how in WORKFLOWS:
        if key not in preds:
            continue
        for scope, sel in (("all", [i for i in ids if i in preds[key]]), ("common", common)):
            pp = {i: score.score_page(gold[next(p for p in pages if p["id"] == i).get("gt_from") or i]["items"],
                                      preds[key][i]) for i in sel}  # fmt: skip
            s = score.summarise(pp, [secs.get(key, {}).get("median", 0.0)])
            table.setdefault(key, {"name": name, "how": how})[scope] = {
                k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()
            }
            table[key][scope]["s_per_page"] = secs.get(key, {}).get("median")
    for i in ids:
        g = gold[next(p for p in pages if p["id"] == i).get("gt_from") or i]["items"]
        per_page[i] = {
            "hits": {k: figure_hits(g, preds[k][i]) for k in preds if i in preds[k]},
            "extra": {
                k: [
                    p
                    for p in preds[k][i]
                    if p.get("value") is not None and figure_hits(g, [p]) == ["missed"] * len(g)
                ][:40]
                for k in preds
                if i in preds[k]
            },  # fmt: skip
        }
    OUT.mkdir(parents=True, exist_ok=True)
    blob = {
        "workflows": table,
        "per_page": per_page,
        "common_pages": len(common),
        "portfolio": portfolio(args.portfolio),
    }
    (OUT / "arena.json").write_text(json.dumps(blob, ensure_ascii=False, default=str), encoding="utf-8")
    write_md(table, len(common))
    for k, v in table.items():
        a = v["all"]
        print(f"{v['name']:<24} pages {a['pages']:>2} P {a['precision']:.2f} R {a['recall']:.2f} "
              f"F1 {a['f1']:.2f} acc-wrong {a['wrong_accepted_share']:.1%} review {a['review_share']:.0%}")  # fmt: skip


def write_md(table: dict, n_common: int) -> None:
    def row(v: dict, s: dict) -> str:
        return (f"| {v['name']} | {s['pages']} | {s['gold']} | {s['precision']:.0%} | {s['recall']:.0%} | "
                f"{s['f1']:.2f} | {s['review_share']:.0%} | {s['accepted_precision']:.0%} | "
                f"{s['wrong_accepted']} ({s['wrong_accepted_share']:.1%}) | {s['bbox_hit_rate']:.0%} | "
                f"{round(s['s_per_page'], 1) if s.get('s_per_page') is not None else '–'} |")  # fmt: skip

    head = ("| Workflow | Pages | Gold fees | Precision | Recall | F1 | Sent to review | Precision (accepted) | "
            "Wrong values accepted | Box on the value | s/page |\n|---|---|---|---|---|---|---|---|---|---|---|")  # fmt: skip
    lines = [
        "# Workflow arena — results",
        "",
        "Generated by `data/specimens/arena/run.py` (SC-5.10). Scoring rules: `data/specimens/strategies/score.py`. "
        "Hand-checked figures: `data/specimens/ocrbench/groundtruth.json`. CPU only.",
        "",
        f"## Same {n_common} pages for every workflow",
        "",
        head,
        *(row(v, v["common"]) for v in table.values()),
        "",
        "## Every page each workflow ran",
        "",
        head,
        *(row(v, v["all"]) for v in table.values()),
        "",
        "## How each workflow works",
        "",
        *(f"- **{v['name']}**: {v['how']}" for v in table.values()),
    ]
    (HERE / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
