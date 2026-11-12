"""Ensembles combine readers' figures but never invent or alter one (SC-5.10)."""

from __future__ import annotations

from ensembles import consensus, union

A = {"label": "Custody fee", "value": "0.25", "bbox": [10, 10, 40, 20], "needs_review": False}
B = {"label": "Entry cost", "value": "3", "bbox": [10, 50, 40, 60], "needs_review": False}
SEEN_A = {"label": "Custody", "value": "0.25", "bbox": [12, 11, 38, 19]}
ELSEWHERE = {"label": "Exit cost", "value": "3", "bbox": [200, 300, 230, 310]}


def test_consensus_flags_what_no_second_reader_saw_at_that_spot() -> None:
    out = consensus([A, B], [[SEEN_A, ELSEWHERE]])
    assert [p["needs_review"] for p in out] == [False, True]  # B's value appears, but elsewhere on the page
    assert [(p["value"], p["bbox"]) for p in out] == [(A["value"], A["bbox"]), (B["value"], B["bbox"])]
    assert B["needs_review"] is False  # inputs untouched


def test_union_adds_only_unseen_figures_and_always_for_review() -> None:
    out = union([A], [SEEN_A, ELSEWHERE, {"label": "x", "value": None}])
    assert out[0] is A and len(out) == 2
    assert out[1]["value"] == "3" and out[1]["needs_review"] and "only_second_reader" in out[1]["reasons"]
