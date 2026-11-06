"""Run every specimen in data/reference/specimen_corpus.csv through the FeeLens extraction pipeline.

It calls the same entry point the upload API uses (``pce.extraction.parsers.extract``)
and applies the API's review rule (unknown type or any warning means ``needs_review``).
It never changes parser code: it measures it.

Usage (after ``python3 data/specimens/tools/fetch.py``):
    cd backend && uv run python ../data/specimens/tools/evaluate.py

Writes:
    artifacts/specimens/results.json   one record per file (git-ignored, may hold snippets)
    data/specimens/RESULTS.md          per-category summary and per-file table (committed)
"""

from __future__ import annotations

import csv
import json
import time
import traceback
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pce.api import MAX_UPLOAD_BYTES
from pce.extraction.models import DocType
from pce.extraction.parsers import EXTRACTOR_VERSION, extract

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "reference" / "specimen_corpus.csv"
FILES = ROOT / "var" / "specimens"
OUT_JSON = ROOT / "artifacts" / "specimens" / "results.json"
OUT_MD = ROOT / "data" / "specimens" / "RESULTS.md"

# Taxonomy code (data/taxonomy/document_types.csv) -> the pipeline's DocType.
# None means the pipeline has no parser for this family yet; the honest outcome is "unknown".
EXPECTED_PIPELINE_TYPE = {
    "kid_priips": DocType.KID,
    "kid_finsa": DocType.KID,
    "insurance_kid": DocType.KID,
    "general_price_list": DocType.TARIFF,
    "custody_tariff": DocType.TARIFF,
    "sp_termsheet": DocType.TERMSHEET,
    "annual_cost_report": DocType.COST_REPORT,
    "cost_disclosure": DocType.COST_REPORT,
    "portfolio_statement": DocType.PORTFOLIO_STATEMENT,
    "factsheet": None,
    "prospectus": None,
    "annual_report_fund": None,
    "insurance_dip": None,
    "mandate_contract": None,
    "other": None,
}

# The fields an analyst needs from each family, checked by fee code / fact key.
KEY_FIELDS = {
    DocType.KID: ["isin_linked", "FUND_ONGOING", "FUND_TRANSACTION", "FUND_ENTRY_CHARGE", "FUND_EXIT_CHARGE"],
    DocType.TARIFF: ["CUSTODY_FEE", "BROKERAGE", "minimum", "issuing_entity"],
    DocType.TERMSHEET: ["isin_linked", "SP_ENTRY_COST", "SP_ONGOING"],
    DocType.COST_REPORT: ["fee_observed"],
}


def bbox_ok(ev: dict) -> bool:
    b, w, h = ev.get("bbox"), ev.get("page_width"), ev.get("page_height")
    if not b or not ev.get("page") or not w or not h:
        return False
    x0, y0, x1, y1 = b
    return 0 <= x0 < x1 <= w + 0.5 and 0 <= y0 < y1 <= h + 0.5


def key_hits(dt: DocType, facts: list[dict], isins: set[str]) -> dict[str, bool]:
    codes = {f.get("fee_code") for f in facts}
    keys = {f["key"] for f in facts}
    hits: dict[str, bool] = {}
    for k in KEY_FIELDS.get(dt, []):
        if k == "isin_linked":
            found = {f.get("isin") for f in facts if f.get("isin")}
            hits[k] = bool(found & isins) if isins else bool(found)
        elif k == "minimum":
            hits[k] = any(key.endswith(":minimum") for key in keys)
        elif k == "issuing_entity":
            hits[k] = "meta:issuing_entity" in keys
        elif k == "fee_observed":
            hits[k] = any(f["kind"] == "fee_observed" for f in facts)
        else:
            hits[k] = k in codes
    return hits


def check_expected(expected: str, facts: list[dict]) -> tuple[int, int, list[str]]:
    """``expected`` is 'fact_key=value; ...' as read from the page text."""
    by_key = {f["key"]: f for f in facts}
    ok = total = 0
    misses = []
    for part in filter(None, (p.strip() for p in expected.split(";"))):
        k, _, v = part.partition("=")
        k, v = k.strip(), v.strip()
        if k == "doc_type":
            continue
        total += 1
        got = by_key.get(k, {}).get("value")
        try:
            match = got is not None and Decimal(got) == Decimal(v)
        except InvalidOperation:
            match = got == v
        ok += match
        if not match:
            misses.append(f"{k}: expected {v}, got {got}")
    return ok, total, misses


def run_one(row: dict) -> dict:
    path = FILES / row["file"]
    exp_type = EXPECTED_PIPELINE_TYPE.get(row["document_type"])
    rec: dict = {
        "file": row["file"],
        "category": row["category"],
        "document_type": row["document_type"],
        "language": row["language"],
        "expected_pipeline_type": exp_type.value if exp_type else "unknown (no parser)",
    }
    if not path.exists():
        rec["error"] = "file missing: run fetch.py"
        return rec
    data = path.read_bytes()
    if len(data) > MAX_UPLOAD_BYTES:
        rec["rejected"] = f"larger than the upload limit ({len(data) // 2**20} MB)"
        return rec
    t0 = time.perf_counter()
    try:
        res, pages = extract(row["file"], data)
    except ValueError as exc:  # the pipeline's own refusal (page limit, not a PDF): an intake result
        rec["rejected"] = str(exc)
        rec["seconds"] = round(time.perf_counter() - t0, 2)
        return rec
    except Exception as exc:  # noqa: BLE001 - a crash on a real file is a result, not a stop
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc(limit=4)
        rec["seconds"] = round(time.perf_counter() - t0, 2)
        return rec
    prof = res.profile
    facts = [f.model_dump() for f in res.facts]
    isins = {i.strip() for i in row.get("isin", "").split(";") if i.strip()}
    with_bbox = [f for f in facts if f["evidence"].get("bbox")]
    rec.update(
        seconds=round(time.perf_counter() - t0, 2),
        predicted_type=prof.doc_type.value,
        type_score=prof.type_score,
        classified_ok=(prof.doc_type == exp_type) if exp_type else prof.doc_type == DocType.UNKNOWN,
        pages=prof.page_count,
        ocr_pages=sum(1 for p in pages if p.engine != "pdfplumber-text"),
        institution=prof.institution,
        jurisdiction=prof.jurisdiction,
        language_detected=prof.language,
        as_of=prof.as_of,
        status="needs_review" if prof.doc_type == DocType.UNKNOWN or prof.warnings else "extracted",
        warnings=prof.warnings,
        n_facts=len(facts),
        kinds=dict(Counter(f["kind"] for f in facts)),
        fee_codes=sorted({f["fee_code"] for f in facts if f.get("fee_code")}),
        facts_with_bbox=len(with_bbox),
        bbox_in_page=sum(bbox_ok(f["evidence"]) for f in with_bbox),
        facts_without_value=sum(1 for f in facts if f["value"] is None),
        key_fields=key_hits(exp_type, facts, isins) if exp_type else {},
        facts=[
            {k: f[k] for k in ("key", "value", "isin", "fee_code", "measurement")}
            | {"page": f["evidence"].get("page"), "bbox": f["evidence"].get("bbox"),
               "snippet": f["evidence"].get("snippet", "")[:160]}
            for f in facts
        ],
    )
    if row.get("expected"):
        ok, total, misses = check_expected(row["expected"], facts)
        rec.update(expected_ok=ok, expected_total=total, expected_misses=misses)
    return rec


def pct(a: int, b: int) -> str:
    return f"{a}/{b}" if b else "–"


def write_md(results: list[dict]) -> None:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    lines = [
        "# Specimen corpus: extraction results",
        "",
        f"Generated by `data/specimens/tools/evaluate.py` with extractor `{EXTRACTOR_VERSION}`. "
        "Do not edit by hand; re-run the script.",
        "",
        "## Per category",
        "",
        "| Category | Files | Crashed | Rejected at intake | Type right | ≥1 fact | Facts | With bbox | Bbox in page | "
        "Key fields hit | Expected values right | Needs review |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    tot = Counter()
    for cat in sorted(by_cat):
        rs = by_cat[cat]
        ok = [r for r in rs if "error" not in r and "rejected" not in r]
        kf = [v for r in ok for v in r.get("key_fields", {}).values()]
        row = Counter(
            files=len(rs),
            crashed=sum("error" in r for r in rs),
            rejected=sum("rejected" in r for r in rs),
            typed=sum(bool(r.get("classified_ok")) for r in ok),
            anyfact=sum(r["n_facts"] > 0 for r in ok),
            facts=sum(r["n_facts"] for r in ok),
            bbox=sum(r["facts_with_bbox"] for r in ok),
            inpage=sum(r["bbox_in_page"] for r in ok),
            kf_hit=sum(kf),
            kf_all=len(kf),
            exp_ok=sum(r.get("expected_ok", 0) for r in ok),
            exp_all=sum(r.get("expected_total", 0) for r in ok),
            review=sum(r["status"] == "needs_review" for r in ok),
        )
        tot.update(row)
        lines.append(
            f"| {cat} | {row['files']} | {row['crashed']} | {row['rejected']} | {pct(row['typed'], len(ok))} | "
            f"{pct(row['anyfact'], len(ok))} | {row['facts']} | {row['bbox']} | {row['inpage']} | "
            f"{pct(row['kf_hit'], row['kf_all'])} | {pct(row['exp_ok'], row['exp_all'])} | "
            f"{pct(row['review'], len(ok))} |"
        )
    n_ok = tot["files"] - tot["crashed"] - tot["rejected"]
    lines.append(
        f"| **All** | {tot['files']} | {tot['crashed']} | {tot['rejected']} | {pct(tot['typed'], n_ok)} | {pct(tot['anyfact'], n_ok)} | "
        f"{tot['facts']} | {tot['bbox']} | {tot['inpage']} | {pct(tot['kf_hit'], tot['kf_all'])} | "
        f"{pct(tot['exp_ok'], tot['exp_all'])} | {pct(tot['review'], n_ok)} |"
    )
    lines += [
        "",
        "Key fields per family: KID = ISIN linked, ongoing, transaction, entry, exit; tariff = custody rate, "
        "brokerage rate, a minimum, issuing entity; termsheet = ISIN linked, entry cost, distribution fee; "
        "cost report = at least one observed fee. Factsheets and prospectuses have no parser yet, so "
        "\"type right\" means the pipeline honestly returned `unknown`.",
        "",
        "## Per file",
        "",
        "| File | Category | Lang | Expected → got | Pages (OCR) | Facts | Bbox ok | Key fields missing | "
        "Expected values | Seconds | Error / first warning |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda r: (r["category"], r["file"])):
        if "rejected" in r:
            lines.append(
                f"| {r['file']} | {r['category']} | {r['language']} | {r['expected_pipeline_type']} → rejected | "
                f"| | | | | {r.get('seconds', '')} | {r['rejected'][:120]} |"
            )
            continue
        if "error" in r:
            lines.append(
                f"| {r['file']} | {r['category']} | {r['language']} | {r['expected_pipeline_type']} → crash | "
                f"| | | | | {r.get('seconds', '')} | {r['error'][:120]} |"
            )
            continue
        missing = ", ".join(k for k, v in r["key_fields"].items() if not v) or "–"
        exp = pct(r.get("expected_ok", 0), r.get("expected_total", 0))
        warn = (r["warnings"][0] if r["warnings"] else "").replace("|", "/")[:100]
        lines.append(
            f"| {r['file']} | {r['category']} | {r['language']} | {r['expected_pipeline_type']} → "
            f"{r['predicted_type']}{'' if r['classified_ok'] else ' ✗'} | {r['pages']} ({r['ocr_pages']}) | "
            f"{r['n_facts']} | {r['bbox_in_page']}/{r['facts_with_bbox']} | {missing} | {exp} | "
            f"{r['seconds']} | {warn} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    results = []
    for row in rows:
        r = run_one(row)
        print(f"{r['file']:<60} {r.get('predicted_type', 'ERR'):<12} facts={r.get('n_facts', '-')}"
              f" {r.get('error', r.get('rejected', ''))}", flush=True)
        results.append(r)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(results)
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
