"""The agent can select and flag candidates but never create or change a figure (SC-5.10, AC #2).

Run: python3 -m pytest data/specimens/arena/test_agent.py (no model or torch needed).
"""

from __future__ import annotations

from agent import apply_decisions, flag_only, parse_json

CANDS = [
    {"label": "Custody fee", "value": "0.25", "bbox": [10, 10, 40, 20], "needs_review": False, "reasons": []},
    {
        "label": "Share price",
        "value": "101.30",
        "bbox": [10, 30, 40, 40],
        "needs_review": False,
        "reasons": [],
    },
    {"label": "Entry cost", "value": "3", "bbox": [10, 50, 40, 60], "needs_review": False, "reasons": []},
]


def test_not_fee_drops_unsure_flags_and_values_never_change() -> None:
    out = apply_decisions(CANDS, {"c1": "fee", "c2": "not_fee", "c3": "unsure"})
    assert [p["label"] for p in out] == ["Custody fee", "Entry cost"]
    assert out[1]["needs_review"] and "agent_unsure" in out[1]["reasons"]
    for p in out:
        src = next(c for c in CANDS if c["label"] == p["label"])
        assert (p["value"], p["bbox"]) == (src["value"], src["bbox"])
    assert CANDS[2]["needs_review"] is False  # the input is not mutated


def test_invented_ids_and_numbers_in_the_answer_cannot_add_figures() -> None:
    answer = parse_json('Sure! {"c1": "fee", "c9": "fee", "c2": "999.99", "new": {"value": "5"}}')
    out = apply_decisions(CANDS, answer)
    assert len(out) == len(CANDS)  # c9 does not exist, "999.99" is not a decision: nothing added or changed
    assert {p["value"] for p in out} == {c["value"] for c in CANDS}


def test_garbled_answer_keeps_every_candidate() -> None:
    assert apply_decisions(CANDS, parse_json("I think c2 is not a fee")) == CANDS
    assert parse_json('<think>{"c1": "not_fee"}</think> no json here') == {}


def test_flag_only_never_drops_a_figure() -> None:
    log = [{"decisions": {"c1": "fee", "c2": "not_fee", "c3": "unsure"}}]
    out = flag_only(CANDS, log)
    assert [p["value"] for p in out] == [c["value"] for c in CANDS]
    assert [p["needs_review"] for p in out] == [False, True, True]
