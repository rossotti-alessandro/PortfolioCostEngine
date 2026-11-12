"""Fee-fact scorer shared by every extraction strategy (SC-5.8).

Matching rules agreed with the accuracy-protocol thread (SC-9.x), so numbers line up:
one-to-one greedy matching per page; a prediction matches a gold fee when the value is equal as a
Decimal after normalisation and the label matches (fee codes equal when both sides carry one,
otherwise at least half of the gold label's words, lowercased, accents stripped, 3+ letters, appear
in the predicted label + evidence snippet).

Metrics: precision, recall, F1; value-only recall; bbox hit (the predicted box holds the centre of the
gold value box); wrong_value (a prediction whose label matches a gold fee on its page but whose value
matches none: confidently wrong) and missing-as-zero (an unmatched predicted 0) counted as wrong
values; needs_review share; median s/page.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from decimal import Decimal

from pce.extraction.numbers import find_numbers


def gold_value(text: str) -> Decimal | None:
    ns = find_numbers(text)
    if not ns:  # a bare integer such as "0" or "100" is still a printed figure in the gold file
        m = re.search(r"\d+", text)
        return Decimal(m.group()) if m else None
    return ns[0].value


def tokens(text: str) -> set[str]:
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return set(re.findall(r"[a-z]{3,}", s))


def label_ok(gold_label: str, pred_text: str) -> bool:
    g = tokens(gold_label)
    if not g:
        return True
    return len(g & tokens(pred_text)) * 2 >= len(g)


def same_value(a: Decimal | None, b: Decimal | None) -> bool:
    # sign conventions differ between documents ("(3.28)" and "3.28 debit"): compare magnitudes
    return a is not None and b is not None and abs(a) == abs(b)


def contains(box: list[float] | None, gold: list[float] | None) -> bool | None:
    if not box or not gold:
        return None
    cx, cy = (gold[0] + gold[2]) / 2, (gold[1] + gold[3]) / 2
    return box[0] - 1 <= cx <= box[2] + 1 and box[1] - 1 <= cy <= box[3] + 1


def score_page(gold: list[dict], preds: list[dict]) -> dict:
    """gold: [{label, value, bbox}]; preds: [{label, snippet, value (str), bbox, needs_review}]."""
    gvals = [gold_value(g["value"]) for g in gold]
    pvals = [Decimal(p["value"]) if p.get("value") not in (None, "") else None for p in preds]
    ptext = [f"{p.get('label', '')} {p.get('snippet', '')}" for p in preds]
    used_g: set[int] = set()
    matched: list[tuple[int, int]] = []
    for pi, p in enumerate(preds):
        for gi, g in enumerate(gold):
            if gi in used_g or not same_value(gvals[gi], pvals[pi]):
                continue
            if p.get("fee_code") and g.get("fee_code"):
                ok = p["fee_code"] == g["fee_code"]
            else:
                ok = label_ok(g["label"], ptext[pi])
            if ok:
                used_g.add(gi)
                matched.append((pi, gi))
                break
    matched_p = {pi for pi, _ in matched}
    wrong = 0
    for pi in range(len(preds)):
        if pi in matched_p:
            continue
        if pvals[pi] == 0 or any(label_ok(g["label"], ptext[pi]) for g in gold):
            wrong += 1
    value_found = sum(1 for gv in gvals if any(same_value(gv, pv) for pv in pvals))
    hits = [contains(preds[pi].get("bbox"), gold[gi].get("bbox")) for pi, gi in matched]
    return {
        "gold": len(gold),
        "pred": len(preds),
        "tp": len(matched),
        "wrong": wrong,
        "value_found": value_found,
        "bbox_hit": sum(1 for h in hits if h),
        "bbox_known": sum(1 for h in hits if h is not None),
        "review": sum(1 for p in preds if p.get("needs_review")),
        "wrong_accepted": sum(
            1
            for pi in range(len(preds))
            if pi not in matched_p
            and not preds[pi].get("needs_review")
            and (pvals[pi] == 0 or any(label_ok(g["label"], ptext[pi]) for g in gold))
        ),
        "tp_accepted": sum(1 for pi, _ in matched if not preds[pi].get("needs_review")),
        "pred_accepted": sum(1 for p in preds if not p.get("needs_review")),
    }


def summarise(per_page: dict[str, dict], seconds: list[float]) -> dict:
    t = {k: sum(p[k] for p in per_page.values()) for k in next(iter(per_page.values()))}
    prec = t["tp"] / t["pred"] if t["pred"] else 0.0
    rec = t["tp"] / t["gold"] if t["gold"] else 0.0
    return {
        **t,
        "pages": len(per_page),
        "precision": prec,
        "recall": rec,
        "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "value_recall": t["value_found"] / t["gold"] if t["gold"] else 0.0,
        "wrong_share": t["wrong"] / t["pred"] if t["pred"] else 0.0,
        "bbox_hit_rate": t["bbox_hit"] / t["bbox_known"] if t["bbox_known"] else 0.0,
        "review_share": t["review"] / t["pred"] if t["pred"] else 0.0,
        "accepted_precision": t["tp_accepted"] / t["pred_accepted"] if t["pred_accepted"] else 0.0,
        "accepted_recall": t["tp_accepted"] / t["gold"] if t["gold"] else 0.0,
        "wrong_accepted_share": t["wrong_accepted"] / t["pred_accepted"] if t["pred_accepted"] else 0.0,
        "s_per_page": statistics.median(seconds) if seconds else 0.0,
    }
