"""End to end on one realistic prospect: statement (as a phone photo) + the real public KIDs of its funds.

``uv run python -m pce.evaluation.realistic.e2e <out_dir> [--layout ch_ticino_it] [--condition photo]``

The statement is SYNTHETIC (fictitious bank and client) and holds real ISINs; the KIDs are the issuers' own
public documents from the specimen corpus (``var/specimens``, fetched by ``data/specimens/tools/fetch.py``).
The app's own ``extract()`` and ``analyse()`` run on the folder exactly as on an upload, and the client
report is rendered. Writes ``analysis.json``, ``report-en.pdf``, ``report-it.pdf`` and ``summary.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path

from ...analysis import analyse
from ...demo.offline import load_folder
from ...demo.spec import PROPOSAL_DEFAULTS
from ...report import render_client_report
from . import degrade
from .generate import LAYOUTS, render
from .universe import ROOT

SPECIMENS = ROOT / "var" / "specimens"


def build_prospect(out: Path, layout: str, condition: str, seed: int = 4242) -> dict:
    docs = out / "documents"
    docs.mkdir(parents=True, exist_ok=True)
    lay = next(x for x in LAYOUTS if x.key == layout)
    src = out / "statement-digital.pdf"
    gold = render(src, lay, seed).__dict__
    data = src.read_bytes()
    if condition != "digital":
        data = {"scan": lambda: degrade.scan(data, seed), "photo": lambda: degrade.photo(data, seed)}[
            condition
        ]()
    (docs / f"statement-{condition}.pdf").write_bytes(data)
    from .universe import funds

    by_isin = {f.isin: f for f in funds()}
    kids = []
    for p in gold["positions"]:
        f = by_isin.get(p["isin"])
        if f and f.kid_file and (SPECIMENS / f.kid_file).exists():
            shutil.copy(SPECIMENS / f.kid_file, docs / f"kid_{p['isin']}.pdf")
            kids.append({"isin": p["isin"], "ocf_pct": str(f.ocf_pct), "value": p["value"]})
    (out / "gold.json").write_text(json.dumps(gold, indent=1), encoding="utf-8")
    return {"gold": gold, "kids": kids}


def expected_product_cost(kids: list[dict]) -> Decimal:
    """Hand-checked OCF x value for every fund whose KID was supplied: what the engine should find."""
    return sum((Decimal(k["value"]) * Decimal(k["ocf_pct"]) / 100 for k in kids), Decimal(0))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path)
    ap.add_argument("--layout", default="ch_ticino_it")
    ap.add_argument("--condition", default="photo", choices=["digital", "scan", "photo"])
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    built = build_prospect(a.out, a.layout, a.condition)
    docs, facts = load_folder(a.out / "documents")
    result = analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)
    (a.out / "analysis.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    client = {k: v for k, v in result.items() if k != "internal"}  # as api.client_safe does
    client["documents"] = docs  # as api.compute adds: nothing checked by a person yet in this run
    client["review"] = {"facts": len(facts), "reviewed": 0, "rejected": 0}
    client["prospect"] = {
        "code": "R-4242",
        "label": "Realistic test prospect (synthetic)",
        "domicile": "CH",
        "synthetic": True,
    }  # as api.compute adds, with the same snapshot hash
    snap = json.dumps({k: result[k] for k in ("current", "scenarios")}, sort_keys=True, default=str)
    client["snapshot_hash"] = hashlib.sha256(snap.encode()).hexdigest()
    client["proposal_inputs"] = {
        k: v for k, v in result.get("proposal_inputs", {}).items() if k != "internal"
    }
    for lang in ("en", "it"):
        (a.out / f"report-{lang}.pdf").write_bytes(render_client_report(client, lang))
    summary = {
        "statement_total": built["gold"]["total"],
        "positions": len(built["gold"]["positions"]),
        "kids_joined": len(built["kids"]),
        "expected_fund_ocf_chf": str(expected_product_cost(built["kids"]).quantize(Decimal("0.01"))),
        "fees_on_statement": built["gold"]["fees"],
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
