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
import random
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
import ensembles  # noqa: E402
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
ZERO_HOW = "Agent flags only, and its opinion on zero charges is ignored (it mistook them for 'no fee')."
for d in sorted((OUT / "agent").glob("*/")):  # one agentic workflow per local model run with agent.py --model
    WORKFLOWS.append((f"agentic:{d.name}", f"Agentic review ({d.name})", f"agent:{d.name}", AGENT_HOW))
    WORKFLOWS.append(
        (f"agentic_flag:{d.name}", f"Agent flags only ({d.name})", f"agentflag:{d.name}", FLAG_HOW)
    )
    WORKFLOWS.append(
        (f"agentic_zero:{d.name}", f"Agent flags, zeros kept ({d.name})", f"agentzero:{d.name}", ZERO_HOW)
    )
WORKFLOWS += [  # ensembles of readers that already ran (ensembles.py)
    ("consensus", "Two readers must agree", "derived:consensus",
     "Finder + verify and the vision reader read the page independently; a figure the vision reader did not "
     "also see (same value, same spot) goes to review. Vision ran on 23 pages."),
    ("consensus_union", "Two readers, nothing dropped", "derived:consensus_union",
     "As above, plus figures only the vision reader found, always sent to review."),
]  # fmt: skip
DERIVED_FROM = {"consensus": ("finder_verify", "vision"), "consensus_union": ("finder_verify", "vision")}


def predictions() -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = {}
    for key, _, dump, _ in WORKFLOWS:
        if dump.startswith("agent:"):
            runs = (OUT / "agent" / dump[6:]).glob("*.json")
            out[key] = {f.stem: json.loads(f.read_text(encoding="utf-8"))["preds"] for f in runs}
        elif dump.startswith(("agentflag:", "agentzero:")):
            cands = json.loads(
                (DUMPS / "finder @text + verify(tesseract crops).json").read_text(encoding="utf-8")
            )
            runs = (OUT / "agent" / dump.partition(":")[2]).glob("*.json")
            zero = dump.startswith("agentzero:")
            out[key] = {
                f.stem: flag_only(cands[f.stem], json.loads(f.read_text(encoding="utf-8"))["log"], zero)
                for f in runs
            }
        elif (f := DUMPS / f"{dump}.json").exists():
            out[key] = json.loads(f.read_text(encoding="utf-8"))
    # Only the vision reader is independent of the finder (the layout variant and the app reuse it), so the
    # ensembles run where the vision reader ran.
    if {"finder_verify", "vision"} <= out.keys():
        fv, vis = out["finder_verify"], out["vision"]
        out["consensus"] = {i: ensembles.consensus(fv[i], [vis[i]]) for i in vis if i in fv}
        out["consensus_union"] = {i: ensembles.union(c, vis[i]) for i, c in out["consensus"].items()}
    return out


def seconds() -> dict[str, dict[str, float]]:
    """Seconds per page as the harness measured them; the agent adds its own model time on top."""
    prev = json.loads((DUMPS / "scores.json").read_text(encoding="utf-8"))
    secs: dict[str, dict[str, float]] = {}
    for key, _, dump, _ in WORKFLOWS:
        if run := prev.get(f"{dump}@all"):
            secs[key] = {"median": run["summary"]["s_per_page"]}
        elif key in DERIVED_FROM:  # readers run one after another: their times add up
            secs[key] = {
                "median": round(sum(secs.get(k, {}).get("median", 0.0) for k in DERIVED_FROM[key]), 2)
            }
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
    table, per_page, page_scores = {}, {}, {}
    gt_of = {p["id"]: p.get("gt_from") or p["id"] for p in pages}
    doc_type = {p["id"]: p.get("document_type") or "other" for p in pages}
    for key, name, _, how in WORKFLOWS:
        if key not in preds:
            continue
        for scope, sel in (("all", [i for i in ids if i in preds[key]]), ("common", common)):
            pp = {i: score.score_page(gold[next(p for p in pages if p["id"] == i).get("gt_from") or i]["items"],
                                      preds[key][i]) for i in sel}  # fmt: skip
            s = score.summarise(pp, [secs.get(key, {}).get("median", 0.0)])
            if scope == "all":
                page_scores[key] = pp
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
        "validation": (val := validation(page_scores, doc_type, gt_of)),
    }
    (OUT / "arena.json").write_text(json.dumps(blob, ensure_ascii=False, default=str), encoding="utf-8")
    write_md(table, len(common), val)
    for k, v in table.items():
        a = v["all"]
        print(f"{v['name']:<24} pages {a['pages']:>2} P {a['precision']:.2f} R {a['recall']:.2f} "
              f"F1 {a['f1']:.2f} acc-wrong {a['wrong_accepted_share']:.1%} review {a['review_share']:.0%}")  # fmt: skip


# Pages the agent prompt was tuned on (SC-5.10 trials). Their scores are reported apart as "held out".
TUNED = {"kid-ff-ch0228419740-p3", "sample-edwardjones-releve-fr-p2", "tariff-bcv-clientele-privee-fr-p12"}


def validation(
    page_scores: dict[str, dict[str, dict]], doc_type: dict[str, str], gt_of: dict[str, str]
) -> dict:
    """How far to trust each score: 95% bootstrap intervals over pages, a held-out score without the pages
    the agent prompt was tuned on, and recall by document type."""
    rng = random.Random(510)
    out = {}
    for key, pp in page_scores.items():
        ids = list(pp)
        draws = []
        for _ in range(1000):
            s = score.summarise({str(n): pp[rng.choice(ids)] for n in range(len(ids))}, [])
            draws.append((s["recall"], s["wrong_accepted_share"], s["review_share"]))
        ci = {m: [round(sorted(d[j] for d in draws)[q], 4) for q in (25, 974)]
              for j, m in enumerate(("recall", "wrong_accepted_share", "review_share"))}  # fmt: skip
        held = {i: v for i, v in pp.items() if gt_of[i] not in TUNED}
        hs = score.summarise(held, [])
        by_type: dict[str, dict] = {}
        for t in sorted({doc_type[i] for i in ids}):
            st = score.summarise({i: v for i, v in pp.items() if doc_type[i] == t}, [])
            by_type[t] = {"pages": st["pages"], "gold": st["gold"], "recall": round(st["recall"], 4)}
        out[key] = {"ci95": ci, "held_out": {"pages": hs["pages"], "recall": round(hs["recall"], 4),
                    "wrong_accepted_share": round(hs["wrong_accepted_share"], 4),
                    "review_share": round(hs["review_share"], 4)}, "by_type": by_type}  # fmt: skip
    return out


def write_md(table: dict, n_common: int, val: dict | None = None) -> None:
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
    if val:
        types = sorted({t for v in val.values() for t in v["by_type"]})
        lines += [
            "",
            "## How far to trust these numbers",
            "",
            "95% intervals from 1000 bootstrap resamples of pages (every page the workflow ran). Held out = "
            f"without the {len(TUNED)} pages (and their scans) the agent prompt was tuned on.",
            "",
            "| Workflow | Recall (95% CI) | Wrong accepted (95% CI) | Review (95% CI) | Held-out recall | Held-out wrong accepted |",
            "|---|---|---|---|---|---|",
            *(f"| {table[k]['name']} | {v['ci95']['recall'][0]:.0%} to {v['ci95']['recall'][1]:.0%} | "
              f"{v['ci95']['wrong_accepted_share'][0]:.1%} to {v['ci95']['wrong_accepted_share'][1]:.1%} | "
              f"{v['ci95']['review_share'][0]:.0%} to {v['ci95']['review_share'][1]:.0%} | "
              f"{v['held_out']['recall']:.0%} | {v['held_out']['wrong_accepted_share']:.1%} |" for k, v in val.items()),
            "",
            "## Recall by document type",
            "",
            "| Workflow | " + " | ".join(types) + " |",
            "|---|" + "---|" * len(types),
            *(f"| {table[k]['name']} | " + " | ".join(
                f"{v['by_type'][t]['recall']:.0%}" if t in v["by_type"] else "–" for t in types) + " |"
              for k, v in val.items()),
            "",
            "Fees per type (gold): " + ", ".join(
                f"{t} {next(v['by_type'][t]['gold'] for v in val.values() if t in v['by_type'])}" for t in types) + ".",
        ]  # fmt: skip
    (HERE / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
