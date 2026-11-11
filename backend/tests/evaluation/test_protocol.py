"""The accuracy protocol scores what it claims to score (SC-9.1).

Unit tests pin the matching rule and the number normaliser. The integration tests run the protocol on
the SYNTHETIC prospects: the production pipeline must pass every gate, and a deliberately wrong
extractor must score lower and fail them (otherwise the scorer is blind).
"""

from decimal import Decimal as Dec
from pathlib import Path

import pytest

from pce.evaluation import provenance
from pce.evaluation.gold import synthetic_p1042
from pce.evaluation.metrics import GoldItem, numbers, score, to_decimal
from pce.evaluation.runner import as_scan, evaluate, gate, invariants, load_corpus
from pce.evaluation.strategies import baseline


@pytest.mark.parametrize(
    ("printed", "value"),
    [
        ("1'234'567.89", "1234567.89"),
        ("900’000.00", "900000.00"),
        ("1.250,50", "1250.50"),
        ("0,9350", "0.9350"),
        ("1,08 %", "1.08"),
        ("1,250,000.5", "1250000.5"),
        ("1 250,00", "1250.00"),
        ("Up to €300", "300"),
    ],
)
def test_numbers_normalised_as_decimal(printed, value):
    assert to_decimal(printed) == Dec(value)


def test_space_is_not_a_thousands_separator():
    # table cells are space-separated: quantity 4'500, price 200.00
    assert numbers("4'500 200.00") == [Dec("4500"), Dec("200.00")]


def _fact(key, value, label="", page=1, bbox=None, fee_code=None, field="rate_pct"):
    return {
        "key": key,
        "field": field,
        "value": value,
        "label": label,
        "fee_code": fee_code,
        "evidence": {"page": page, "bbox": bbox, "snippet": label},
    }


def test_outcomes_correct_wrong_missed_and_missing_as_zero():
    gold = [
        GoldItem(file="x", key="fee:A", value="10.00"),
        GoldItem(file="x", key="fee:B", value="5"),
        GoldItem(file="x", key="sp:margin", value=None),  # not disclosed: must stay unknown
        GoldItem(file="x", key="fee:C", value="1"),
    ]
    facts = [_fact("fee:A", "10"), _fact("fee:B", "50"), _fact("sp:margin", "0"), _fact("fee:X", "7")]
    s = score(gold, facts)
    assert [o.status for o in s.outcomes] == ["correct", "wrong_value", "wrong_value", "missed"]
    assert s.missing_as_zero == 1 and s.correct == 1 and s.predicted == 4
    assert s.precision == 0.25 and s.recall == 0.25 and s.wrong_value_rate == 2 / 3


def test_unknown_stays_unknown_is_correct():
    s = score([GoldItem(file="x", key="sp:margin", value=None)], [_fact("sp:margin", None)])
    assert s.correct == 1 and s.missing_as_zero == 0


def test_label_rule_and_page_and_bbox():
    gold = [GoldItem(file="x", label="Ongoing charges", value="1.08%", page=2, bbox=[100, 100, 120, 110])]
    on_wrong_page = _fact("k", "1.08", "Ongoing charges", page=1)
    right = _fact("k", "1.08", "Ongoing charges (OCF)", page=2, bbox=[50, 95, 500, 115])
    s = score(gold, [on_wrong_page, right])
    assert s.correct == 1 and s.bbox_hit_rate == 1.0 and s.outcomes[0].fact is right


def test_partial_labels_give_no_precision():
    s = score([GoldItem(file="x", key="fee:A", value="1")], [_fact("fee:A", "1"), _fact("fee:Z", "2")], False)
    assert s.recall == 1.0 and s.precision is None


@pytest.fixture(scope="module")
def p1042(tmp_path_factory):
    return load_corpus("synthetic-p1042", tmp_path_factory.mktemp("eval"))


def test_provenance_flags_a_box_that_does_not_hold_the_value(p1042):
    path: Path = p1042.folder / "alpha_statement_of_assets_2026-09-30.pdf"
    data = path.read_bytes()
    facts = baseline(path.name, data).facts
    assert provenance.check(path.name, data, facts)["mismatch"] == 0
    a, b = facts[0]["evidence"]["bbox"], facts[1]["evidence"]["bbox"]
    facts[0]["evidence"]["bbox"], facts[1]["evidence"]["bbox"] = b, a  # each value points at the other row
    assert provenance.check(path.name, data, facts)["mismatch"] == 2


def test_scan_variant_has_no_text_layer(p1042):
    path = p1042.folder / "kid_ZZGEQLDRA013.pdf"
    data = as_scan(path.name, path.read_bytes())
    facts = [_fact("k", "1.08", page=1, bbox=[0, 0, 500, 500])]
    assert provenance.check(path.name, data, facts) == {"unverifiable": 1}


def test_golden_labels_come_from_the_generator_inputs_not_the_parser(tmp_path):
    c = synthetic_p1042(tmp_path)
    items = {(d.file, i.key): i.value for d in c.docs for i in d.items}
    assert items[("kid_ZZGEQLDRA013.pdf", "kid:FUND_ONGOING")] == "1.08"
    assert items[("termsheet_ZZBRCSMI0010.pdf", "sp:entry_cost")] is None


@pytest.mark.ocr  # the P-1042 cash statement is a scan
def test_baseline_passes_every_gate_and_sabotage_fails(p1042):
    good = evaluate(p1042, "baseline", "digital")
    bad = evaluate(p1042, "sabotaged", "digital")
    assert gate(good) == [], good
    assert good["recall"] == 1.0 and good["portfolio_mismatches"] == 0 and good["invariant_failures"] == 0
    assert bad["recall"] < good["recall"] and bad["wrong_value"] > 0 and bad["missing_as_zero"] > 0
    assert bad["portfolio_mismatches"] > 0 and not bad["silent_error"]  # the checks raised an alarm
    assert gate(bad)


def test_invariants_catch_double_count_and_missing_as_number():
    led = {
        "total_known": "100",
        "billed_known": "100",
        "embedded_known": "0",
        "one_off_known": "0",
        "atoms": [
            {
                "id": "a",
                "amount": "100",
                "role": "counted",
                "measurement": "observed",
                "included_in": None,
                "evidence_fact_ids": [1],
            },
            {
                "id": "b",
                "amount": "60",
                "role": "counted",
                "measurement": "estimated",
                "included_in": None,
                "evidence_fact_ids": [],
            },
            {
                "id": "c",
                "amount": "0",
                "role": "unknown",
                "measurement": "unknown",
                "included_in": None,
                "evidence_fact_ids": [],
            },
        ],
    }
    fails = invariants({"current": led, "scenarios": {"same_holdings": {"ledger": led}}})
    text = " ".join(fails)
    assert "double count" in text and "missing became a number" in text and "not traceable" in text
