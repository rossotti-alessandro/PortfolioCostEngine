"""Run strategies over corpora and variants, score every stage, apply the gates, write the report.

Usage (from backend/):
    uv run python -m pce.evaluation                     # synthetic corpora, baseline + sabotaged
    uv run python -m pce.evaluation --strategy baseline --variant digital,scan
    uv run python -m pce.evaluation --corpus ocrbench,specimen_corpus  # needs var/specimens (fetch.py)
    uv run python -m pce.evaluation --strategy mypkg.mymodule:extract  # any new strategy

Writes ``artifacts/eval/<UTC-ts>/report.md`` and ``results.json`` (git-ignored: may hold snippets of
public documents). Exit code 1 when a gated strategy fails a gate.
"""

from __future__ import annotations

import argparse
import io
import json
import statistics
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from ..analysis import analyse
from ..demo import archetypes, generate, spec
from . import gold as G
from . import provenance
from .metrics import Scores, score
from .strategies import Prediction, resolve

ROOT = G.ROOT
CORPORA = ("synthetic-p1042", "synthetic-p2077", "ocrbench", "specimen_corpus")

# A strategy becomes the default only if it passes all of these on the synthetic corpora (digital).
GATES = {
    "classification_accuracy": ("min", 1.0),
    "recall": ("min", 0.98),
    "precision": ("min", 0.98),
    "wrong_value_rate": ("max", 0.01),
    "missing_as_zero": ("max", 0),
    "provenance_mismatch": ("max", 0),
    "portfolio_mismatches": ("max", 0),
    "silent_error": ("max", False),
    "invariant_failures": ("max", 0),
}


def load_corpus(name: str, workdir: Path) -> G.Corpus:
    if name == "synthetic-p1042":
        out = workdir / "p1042"
        out.mkdir(parents=True, exist_ok=True)
        generate.generate(out)
        return G.synthetic_p1042(out)
    if name == "synthetic-p2077":
        out = workdir / "p2077"
        out.mkdir(parents=True, exist_ok=True)
        archetypes.generate(out)
        return G.synthetic_p2077(out)
    if name == "ocrbench":
        return G.ocrbench()
    if name == "specimen_corpus":
        return G.manifest()
    raise ValueError(f"unknown corpus {name!r}: {CORPORA}")


def as_scan(filename: str, data: bytes, dpi: int = 150) -> bytes:
    """Image-only copy of a PDF (no text layer), as a scanner would deliver it. Spreadsheets unchanged."""
    if not filename.lower().endswith(".pdf"):
        return data
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    images = [pdf[i].render(scale=dpi / 72, grayscale=True).to_pil() for i in range(len(pdf))]
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:], resolution=dpi)
    return buf.getvalue()


def _get(tree: dict, path: str) -> object:
    for part in path.split("."):
        tree = tree.get(part) if isinstance(tree, dict) else None  # type: ignore[assignment]
    return tree


def _same(got: object, want: str | bool) -> bool:
    if isinstance(want, bool) or got is None:
        return got == want
    try:
        return Decimal(str(got)) == Decimal(want)
    except ArithmeticError:
        return False


def invariants(a: dict) -> list[str]:
    """Rules that hold for any analysis, labelled or not. Returns the failures."""
    fails = []
    for name, led in (
        ("current", a["current"]),
        ("same_holdings", a["scenarios"]["same_holdings"]["ledger"]),
    ):
        atoms = led["atoms"]
        if Decimal(led["total_known"]) != Decimal(led["billed_known"]) + Decimal(
            led["embedded_known"]
        ) + Decimal(led["one_off_known"]):
            fails.append(f"{name}: total_known != billed + embedded + one-off")
        counted = sum(
            (Decimal(x["amount"]) for x in atoms if x["role"] == "counted" and x["amount"]), Decimal(0)
        )
        if counted != Decimal(led["total_known"]):
            fails.append(
                f"{name}: counted atoms {counted} != total_known {led['total_known']} (double count?)"
            )
        for x in atoms:
            if x["measurement"] == "unknown" and x["amount"] is not None:
                fails.append(f"{name}: {x['id']} is unknown but carries an amount (missing became a number)")
            if x["measurement"] in ("illustrative", "maximum") and x["role"] == "counted":
                fails.append(f"{name}: {x['id']} is {x['measurement']} but counted as paid")
            if x["role"] == "included_in_parent" and not x["included_in"]:
                fails.append(f"{name}: {x['id']} included in no parent")
        if name == "current":
            for x in atoms:
                if x["role"] == "counted" and not x["evidence_fact_ids"]:
                    fails.append(f"current: {x['id']} counted with no source fact (not traceable)")
    return fails


def evaluate(corpus: G.Corpus, strategy_name: str, variant: str) -> dict:
    strategy = resolve(strategy_name)
    cls_ok = cls_n = 0
    totals = Scores()
    prov: Counter = Counter()
    seconds, review, per_doc, documents, facts = [], 0, [], [], []
    fid = 0
    for i, gd in enumerate(corpus.docs, start=1):
        path = corpus.folder / gd.file
        if not path.exists():
            per_doc.append({"file": gd.file, "skipped": "file not present (fetch the corpus)"})
            continue
        data = path.read_bytes()
        if variant == "scan":
            data = as_scan(gd.file, data)
        t0 = time.perf_counter()
        try:
            pred: Prediction = strategy(gd.file, data)
        except Exception as exc:  # a crash is a result, scored as all-missed
            pred = Prediction(doc_type="error", facts=[], needs_review=True)
            per_doc.append({"file": gd.file, "error": f"{type(exc).__name__}: {exc}"})
        dt = time.perf_counter() - t0
        seconds.append(dt / max(1, pred.pages))
        review += pred.needs_review
        if gd.doc_type:
            cls_n += 1
            cls_ok += pred.doc_type == gd.doc_type
        scoped = [
            f
            for f in pred.facts
            if (gd.kinds is None or f.get("kind") in gd.kinds)
            and (gd.pages is None or (f.get("evidence") or {}).get("page") in gd.pages)
            and not (f.get("kind") == "meta" and f.get("value") is None)  # institution names: not a value
        ]
        s = score(gd.items, scoped, exhaustive=gd.exhaustive)
        totals.add(s)
        p = provenance.check(gd.file, data, scoped)
        prov.update(p)
        per_doc.append(
            {
                "file": gd.file,
                "doc_type": pred.doc_type,
                "expected_type": gd.doc_type,
                **s.summary(),
                "provenance": dict(p),
                "errors": [
                    {
                        "label": o.gold.key or o.gold.label,
                        "want": o.gold.value,
                        "status": o.status,
                        "got": None if o.fact is None else o.fact.get("value"),
                    }
                    for o in s.outcomes
                    if o.status != "correct"
                ],
                "seconds": round(dt, 2),
            }
        )
        documents.append({"id": i, "filename": gd.file, "doc_type": pred.doc_type, "profile": pred.profile})
        for f in pred.facts:
            fid += 1
            facts.append({**f, "id": fid, "document_id": i, "status": "extracted"})

    out: dict = {
        "corpus": corpus.name,
        "strategy": strategy_name,
        "variant": variant,
        "documents": len(documents),
        "classification_accuracy": round(cls_ok / cls_n, 4) if cls_n else None,
        **totals.summary(),
        "provenance": dict(prov),
        "provenance_mismatch": prov["mismatch"],
        "needs_review_share": round(review / len(documents), 4) if documents else None,
        "median_seconds_per_page": round(statistics.median(seconds), 3) if seconds else None,
        "per_document": per_doc,
    }
    if corpus.portfolio and documents:
        a = analyse({"domicile": corpus.domicile}, documents, facts, spec.PROPOSAL_DEFAULTS)
        gp = corpus.portfolio
        mism = [
            {"path": k, "want": str(v), "got": str(_get(a, k))}
            for k, v in gp.expect.items()
            if not _same(_get(a, k), v)
        ]
        req = {r["key"] for r in a["requests"]}
        mism += [
            {"path": f"requests[{k}]", "want": "raised", "got": "absent"} for k in gp.requests if k not in req
        ]
        failed = {c["key"] for c in a["checks"] if c["status"] == "fail"}
        mism += [
            {"path": f"checks[{k}]", "want": "fail", "got": "not failed"}
            for k in gp.failed_checks
            if k not in failed
        ]
        inv = invariants(a)
        # Detectability: a wrong total must trip at least one validation check (or an unexpected warning)
        # so the analyst is told to look. A wrong total with nothing flagged is a silent error.
        alarms = sorted(
            (failed - set(gp.failed_checks)) | {c["key"] for c in a["checks"] if c["status"] == "warn"}
        )
        out.update(
            portfolio_mismatches=len(mism),
            portfolio=mism,
            silent_error=bool(mism) and not alarms,
            alarms=alarms,
            invariant_failures=len(inv),
            invariants=inv,
        )
    return out


def gate(row: dict) -> list[str]:
    fails = []
    for metric, (kind, bound) in GATES.items():
        v = row.get(metric)
        if v is None:
            continue
        if (kind == "min" and v < bound) or (kind == "max" and v > bound):
            fails.append(f"{metric}={v} ({kind} {bound})")
    return fails


def _fmt(v: object) -> str:
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "YES" if v else "no"
    if isinstance(v, float):
        return f"{v:.1%}"
    return str(v)


def report(rows: list[dict], stamp: str) -> str:
    cols = [
        ("classification_accuracy", "type ok"),
        ("recall", "recall"),
        ("precision", "precision"),
        ("f1", "F1"),
        ("wrong_value", "wrong #"),
        ("wrong_value_rate", "wrong %"),
        ("missing_as_zero", "missing→0"),
        ("value_recall", "value recall"),
        ("bbox_hit_rate", "bbox hit"),
        ("provenance_mismatch", "prov. bad"),
        ("portfolio_mismatches", "total errs"),
        ("silent_error", "silent"),
        ("invariant_failures", "invariant errs"),
        ("needs_review_share", "review %"),
    ]
    lines = [
        f"# Accuracy evaluation {stamp}",
        "",
        "Protocol: `docs/EVALUATION_PROTOCOL.md`. Generated by `python -m pce.evaluation`; "
        "do not edit by hand.",
        "Gates apply to synthetic corpora, digital variant. `–` = not defined (no labels of that kind).",
        "",
        "| corpus | variant | strategy | docs | " + " | ".join(c[1] for c in cols) + " | s/page | gate |",
        "|" + "---|" * (len(cols) + 6),
    ]
    for r in rows:
        g = r.get("gate")
        lines.append(
            f"| {r['corpus']} | {r['variant']} | {r['strategy']} | {r['documents']} | "
            + " | ".join(_fmt(r.get(c[0])) for c in cols)
            + f" | {r['median_seconds_per_page']} | {'–' if g is None else ('PASS' if not g else 'FAIL')} |"
        )
    for r in rows:
        bad = [d for d in r["per_document"] if d.get("errors") or d.get("error") or d.get("skipped")]
        issues = r.get("portfolio", []) + [
            {"path": "invariant", "want": "", "got": x} for x in r.get("invariants", [])
        ]
        if not bad and not issues and not r.get("gate"):
            continue
        lines += ["", f"## {r['corpus']} / {r['variant']} / {r['strategy']}", ""]
        if r.get("gate"):
            lines.append("**Gate failures:** " + "; ".join(r["gate"]))
        if r.get("portfolio"):
            lines.append(f"Validation alarms raised: {', '.join(r['alarms']) or 'NONE (silent error)'}")
        for i in issues:
            lines.append(f"- portfolio `{i['path']}`: want {i['want']}, got {i['got']}")
        for d in bad[:40]:
            if d.get("skipped") or d.get("error"):
                lines.append(f"- `{d['file']}`: {d.get('skipped') or d.get('error')}")
                continue
            errs = ", ".join(
                f"{e['label']} {e['status']} (want {e['want']}, got {e['got']})" for e in d["errors"][:8]
            )
            more = f" … +{len(d['errors']) - 8}" if len(d["errors"]) > 8 else ""
            lines.append(f"- `{d['file']}` ({d['doc_type']}): {errs}{more}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default="synthetic-p1042,synthetic-p2077")
    ap.add_argument("--strategy", default="baseline,sabotaged")
    ap.add_argument("--variant", default="digital", help="digital, scan (image-only copy, forces OCR)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--gate", default="baseline", help="strategies whose gate failure sets the exit code")
    args = ap.parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or ROOT / "artifacts" / "eval" / stamp
    out.mkdir(parents=True, exist_ok=True)
    gated = set(args.gate.split(","))
    rows, failed = [], False
    with tempfile.TemporaryDirectory() as tmp:
        for cname in args.corpus.split(","):
            corpus = load_corpus(cname, Path(tmp))
            for variant in args.variant.split(","):
                for strat in args.strategy.split(","):
                    row = evaluate(corpus, strat, variant)
                    if cname.startswith("synthetic") and variant == "digital":
                        row["gate"] = gate(row)
                        failed |= strat in gated and bool(row["gate"])
                    rows.append(row)
                    print(
                        f"{cname:16} {variant:8} {strat:24} recall={_fmt(row['recall'])} "
                        f"wrong={row['wrong_value']} gate={row.get('gate')}",
                        file=sys.stderr,
                    )
    (out / "results.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    (out / "report.md").write_text(report(rows, stamp), encoding="utf-8")
    print(out / "report.md")
    return 1 if failed else 0
