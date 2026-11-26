"""Measure the expert agent (SC-5.24) on the realistic statements and on the ocrbench fee pages.

For every item the pipeline escalates (a doubtful value, a possible miss) the proposal is scored against the
gold figures:

- right: confirm of a right reading, correct to a gold value, new = a gold fee the pipeline did not read,
  not_a_fee on a reading that matches no gold figure.
- wrong: confirm of a wrong reading, correct/new to a non-gold value, not_a_fee on a right reading.
- no help: abstain, or an answer the guards dropped.

``recovered`` counts gold fees the pipeline missed (no accepted or flagged value) that a ``new`` or
``correct`` proposal now offers for confirmation.

    uv run python -m pce.evaluation.expert_bench realistic --n 12 --variants scan_poor,photo_hard
    uv run python -m pce.evaluation.expert_bench ocrbench --pages var/ocrbench/pages
Needs a local OpenAI-compatible server (``PCE_EXPERT_URL``), e.g. llama.cpp or Ollama.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pce.extraction import expert
from pce.extraction.parsers import extract

POSITIONS_PER_DOC = 5  # holdings also reconcile to the printed total; sample them, keep every fee item


def _dec(v: object) -> Decimal | None:
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def score(item: expert.Item, p: expert.Proposal, truth: set[Decimal] | None) -> str:
    """``truth``: the gold values for this item (one for a holding, the page's fees otherwise)."""
    if truth is None or p.action == "abstain" or p.dropped:
        return "no_help"
    reading = _dec(item.value)
    if p.action == "not_a_fee":
        return "right" if item.kind == "doubt" and reading not in truth else "wrong"
    proposed = _dec(p.value)
    if p.action == "confirm":
        return "right" if reading in truth else "wrong"
    return "right" if proposed in truth else "wrong"


def _cap(items: list[expert.Item]) -> list[expert.Item]:
    pos = [i for i in items if i.fact_key and i.fact_key.startswith("position")]
    return [i for i in items if i not in pos] + pos[:POSITIONS_PER_DOC]


def _extract_realistic(args: tuple[str, str, dict, int]) -> tuple:
    from pce.evaluation.realistic.__main__ import _variant_bytes

    folder, variant, gold, seed = args
    pdf = (Path(folder) / gold["file"]).read_bytes()
    data = _variant_bytes(variant, pdf, gold, seed)
    res, pages = extract(gold["file"], data)
    return variant, gold, data, res, pages


def run_doc(res, pages, data, truth_for, chat, model) -> list[dict]:
    by_page = {p.number: p for p in pages}
    reread = expert.pixel_reader(data)
    rows = []
    for item in _cap(expert.escalate(res)):
        page = by_page.get(item.page)
        if not page or not page.lines:
            continue
        p = expert.ask(item, page, chat, model, reread)
        truth = truth_for(item)
        rows.append(
            {
                "kind": item.kind,
                "holding": bool(item.fact_key and item.fact_key.startswith("position")),
                "label": item.label[:60],
                "reading": item.value,
                "action": p.action,
                "value": p.value,
                "dropped": p.dropped,
                "steps": p.steps,
                "seconds": p.seconds,
                "verdict": score(item, p, truth),
                "gold": sorted(map(str, truth)) if truth and len(truth) < 6 else None,
            }
        )
    return rows


def realistic(n: int, variants: list[str], chat, model, out: Path) -> list[dict]:
    from pce.evaluation.realistic import degrade
    from pce.evaluation.realistic.generate import build

    golds = build(out / "documents", n)
    degrade.ensure_fonts()
    jobs = [(str(out / "documents"), v, g.__dict__, 1000 + i) for v in variants for i, g in enumerate(golds)]
    rows: list[dict] = []
    with ProcessPoolExecutor(4) as pool:  # read everything first: OCR and the model must not share the CPU
        extracted = list(pool.map(_extract_realistic, jobs))
    for variant, gold, data, res, pages in extracted:
        fees = {Decimal(x["value"]) for x in gold["fees"]}
        fee_page = gold["fees"][0]["page"] if gold["fees"] else None
        by_isin = {p["isin"]: Decimal(p["value"]) for p in gold["positions"]}
        facts = {f.key: f for f in res.facts}

        def truth_for(item, fees=fees, fee_page=fee_page, by_isin=by_isin, facts=facts):
            f = facts.get(item.fact_key or "")
            if f is not None and f.kind == "position":
                return {by_isin[f.isin]} if f.isin in by_isin else set()
            return fees if item.page == fee_page else set()

        # gold fees the pipeline did not read at all on the fee page
        read = {_dec(f.value) for f in res.facts if f.fee_code and f.evidence.page == fee_page}
        missed = fees - read
        doc_rows = run_doc(res, pages, data, truth_for, chat, model)
        got = {_dec(r["value"]) for r in doc_rows if r["verdict"] == "right" and r["action"] != "confirm"}
        for r in doc_rows:
            r.update(file=gold["file"], variant=variant)
        rows += doc_rows
        rows.append(
            {"file": gold["file"], "variant": variant, "summary": True,
             "fees_gold": len(fees), "fees_missed": len(missed), "recovered": len(missed & got)}
        )  # fmt: skip
        print(variant, gold["file"], len(doc_rows), "items", flush=True)
    return rows


def ocrbench(pages_dir: Path, chat, model) -> list[dict]:
    """One PDF page per ocrbench case (``var/ocrbench/pages/<case>.pdf``, cut from the corpus files);
    gold: the hand-checked fee figures of ``groundtruth.json``. Pages are single, so page 1 holds the gold."""
    from pce.evaluation.gold import OCRBENCH_GT

    gt = json.loads(Path(OCRBENCH_GT).read_text(encoding="utf-8"))["pages"]
    rows: list[dict] = []
    for case, g in gt.items():
        pdf = pages_dir / f"{case}.pdf"
        if not pdf.exists():
            continue
        data = pdf.read_bytes()
        res, pages = extract(pdf.name, data)
        vals = {v for v in (_dec(x["value"]) for x in g["items"]) if v is not None}
        read = {_dec(f.value) for f in res.facts if f.value is not None}
        missed = vals - read
        doc_rows = run_doc(res, pages, data, lambda item, vals=vals: vals, chat, model)
        got = {_dec(r["value"]) for r in doc_rows if r["verdict"] == "right" and r["action"] != "confirm"}
        for r in doc_rows:
            r.update(file=case, variant="ocrbench")
        rows += doc_rows
        rows.append({"file": case, "variant": "ocrbench", "summary": True, "fees_gold": len(vals),
                     "fees_missed": len(missed), "recovered": len(missed & got)})  # fmt: skip
        print(case, len(doc_rows), "items", flush=True)
    return rows


def summarise(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for v in dict.fromkeys(r["variant"] for r in rows):
        items = [r for r in rows if r["variant"] == v and not r.get("summary")]
        docs = [r for r in rows if r["variant"] == v and r.get("summary")]
        verdicts = Counter(r["verdict"] for r in items)
        answered = verdicts["right"] + verdicts["wrong"]
        out[v] = {
            "docs": len(docs),
            "items": len(items),
            "fee_items": sum(not r["holding"] for r in items),
            "actions": dict(Counter(r["action"] for r in items)),
            "dropped_by_guards": sum(bool(r["dropped"]) for r in items),
            "right": verdicts["right"],
            "wrong": verdicts["wrong"],
            "no_help": verdicts["no_help"],
            "right_of_answered_pct": round(100 * verdicts["right"] / answered, 1) if answered else None,
            "fees_missed_by_pipeline": sum(d["fees_missed"] for d in docs),
            "recovered_for_review": sum(d["recovered"] for d in docs),
            "seconds_per_item": round(sum(r["seconds"] for r in items) / len(items), 1) if items else None,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("set", choices=["realistic", "ocrbench"])
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--variants", default="scan_poor,photo_hard")
    ap.add_argument("--pages", type=Path, default=Path("var/ocrbench/pages"))
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = a.out or Path("artifacts/expert") / f"{a.set}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    chat, model = expert.client()
    if a.set == "realistic":
        rows = realistic(a.n, a.variants.split(","), chat, model, out)
    else:
        rows = ocrbench(a.pages, chat, model)
    summary = summarise(rows)
    (out / "results.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
