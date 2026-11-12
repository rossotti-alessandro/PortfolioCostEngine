"""Score holdings and AUM on real public sample statements against hand-checked gold (SC-9.6).

Run from backend/:  uv run python ../data/specimens/statements/score.py [--out RESULTS.md]
PDFs come from var/specimens (python3 data/specimens/tools/fetch.py). Each statement goes through the
app's own extract() and analyse(), one statement per prospect, exactly as an upload would.

What it measures, per statement:
- position recall: gold holdings found on the right page with the exact value (Decimal, no tolerance);
- wrong values: holdings the app read on a gold page whose value matches no gold holding there;
- wrong currency: holdings labelled with a currency other than the statement's;
- AUM error: the app's AUM (sum of holdings read, statement currency) against the hand-checked total, and whether any check raised an alarm.
  A large AUM error with no alarm is a silent error, the outcome the product must never produce.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from pce.demo.offline import run
from pce.extraction.parsers import extract

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPECIMENS = ROOT / "var" / "specimens"
ALARM_PCT = Decimal("1")  # an AUM off by more than 1% must raise an alarm


def score_one(name: str, gold: dict) -> dict:
    path = SPECIMENS / name
    res, _ = extract(name, path.read_bytes())
    pos = [f for f in res.facts if f.kind == "position" and f.value is not None]
    row: dict = {"file": name, "doc_type": res.profile.doc_type.value, "read": len(pos)}
    want = gold.get("positions")
    if want:
        pages = {g["page"] for g in want}
        left = [(f.evidence.page if f.evidence else None, Decimal(f.value)) for f in pos]
        found = 0
        for g in want:
            key = (g["page"], Decimal(g["value"]))
            if key in left:
                left.remove(key)
                found += 1
        row["gold"] = len(want)
        row["found"] = found
        row["wrong_value"] = sum(1 for p, _ in left if p in pages)
    row["wrong_currency"] = sum(1 for f in pos if f.currency != gold["currency"])
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(path, Path(tmp) / name)
        a = run(Path(tmp))
    # In the statement's own currency, as the app reconciles it: the CHF total needs an FX rate printed
    # on the client's documents, which these foreign samples lack (that alarm is expected, not counted).
    aum = sum((Decimal(f.value) for f in pos), Decimal(0)) if pos else None
    truth = Decimal(gold["holdings_total"])
    row["aum_gold"] = str(truth)
    row["aum_app"] = str(aum) if aum is not None else "none"
    err = abs(aum - truth) / truth * 100 if aum is not None else None
    row["aum_error_pct"] = f"{err:.1f}" if err is not None else "n/a"
    alarms = [c["key"] for c in a.get("checks", []) if c.get("status") not in ("pass", "info") and not c["key"].startswith("fx_missing")]
    row["alarms"] = alarms
    row["silent_aum_error"] = bool(err is not None and err > ALARM_PCT and not alarms)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    gold = {k: v for k, v in json.loads((HERE / "gold.json").read_text()).items() if not k.startswith("_")}
    rows = [score_one(n, g) for n, g in gold.items() if (SPECIMENS / n).exists()]
    lines = [
        "| Statement | Type read | Holdings read | Gold holdings found | Wrong values | Wrong currency "
        "| AUM gold | AUM app | AUM error % | Alarms | Silent AUM error |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        found = f"{r['found']}/{r['gold']}" if "gold" in r else "accounts only"
        lines.append(
            f"| {r['file']} | {r['doc_type']} | {r['read']} | {found} | {r.get('wrong_value', '-')} "
            f"| {r['wrong_currency']} | {r['aum_gold']} | {r['aum_app']} | {r['aum_error_pct']} "
            f"| {len(r['alarms'])} | {'YES' if r['silent_aum_error'] else 'no'} |"
        )
    text = "\n".join(lines)
    print(text)
    print(json.dumps([{k: r[k] for k in ("file", "alarms")} for r in rows], indent=1))
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
