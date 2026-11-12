"""Review points: each rule fires on its trigger and stays quiet otherwise (SYNTHETIC inputs)."""

from pce.review_points import review_points


def atom(i, amount="1000.00", role="counted", **kw):
    base = {
        "id": i,
        "label": f"line {i}",
        "fee_label": "Fee",
        "fee_code": "CUSTODY_FEE",
        "institution": "Bank X (Synthetic)",
        "amount": amount,
        "rate_bps": None,
        "measurement": "observed",
        "materiality": "material",
        "role": role,
        "evidence_fact_ids": [1],
        "evidence": [{"fact_id": 1, "confidence": 1.0, "status": "accepted", "review": None}],
    }
    return {**base, **kw}


def run(atoms, checks=(), total="100000.00", assets="10000000"):
    return review_points(
        {
            "current": {"total_known": total, "atoms": atoms},
            "aum": {"by_institution": {"Bank X (Synthetic)": assets}},
            "checks": list(checks),
        }
    )


def kinds(points):
    return [p["kind"] for p in points]


def test_clean_line_raises_nothing():
    assert run([atom("a")]) == []


def test_unknown_is_high_and_never_given_an_amount():
    (p,) = run([atom("u", amount=None, role="unknown", measurement="unknown", evidence=[])])
    assert p["kind"] == "not_determined" and p["severity"] == "high" and p["amount"] is None


def test_low_confidence_source():
    ev = [{"fact_id": 7, "confidence": 0.62, "status": "accepted", "review": None}]
    (p,) = run([atom("a", evidence=ev)])
    assert p["kind"] == "low_confidence" and p["fact_ids"] == [7] and p["vars"]["confidence"] == "0.62"


def test_extraction_review_flag_is_passed_through():
    ev = [
        {
            "fact_id": 3,
            "confidence": 1.0,
            "status": "accepted",
            "review": {"status": "needs_review", "reasons": ["engines_disagree"]},
        }
    ]
    (p,) = run([atom("a", evidence=ev)])
    assert p["kind"] == "extraction_flag" and p["vars"]["reasons"] == "engines_disagree"


def test_unreviewed_only_when_material_share():
    ev = [{"fact_id": 1, "confidence": 1.0, "status": "extracted", "review": None}]
    assert "unreviewed" in kinds(run([atom("a", amount="6000.00", evidence=ev)]))
    assert "unreviewed" not in kinds(run([atom("a", amount="4000.00", evidence=ev)]))


def test_rate_above_review_threshold_uses_bank_assets():
    # 60'000 on 10m = 60 bps of custody, threshold 50
    p = [x for x in run([atom("a", amount="60000.00")]) if x["kind"] == "rate_high"]
    assert p and p[0]["vars"] == {"label": "line a", "bps": "60.0", "limit": "50"}


def test_large_driver_and_list_price_and_corrected():
    ev = [
        {
            "fact_id": 1,
            "confidence": 1.0,
            "status": "corrected",
            "review": None,
            "value": "30000.00",
            "value_extracted": "3000.00",
        }
    ]
    got = kinds(
        run(
            [atom("a", amount="30000.00", measurement="public_tariff", evidence=ev)],
            total="40000.00",
            assets="1000000000",
        )
    )
    assert set(got) == {"corrected", "list_price", "large_driver"}


def test_linked_and_illustrative_lines_are_ignored():
    assert (
        run(
            [
                atom("c", role="included_in_parent", amount="99999.00"),
                atom("d", role="not_a_paid_cost", amount="99999.00"),
            ]
        )
        == []
    )


def test_failed_checks_rank_before_warnings():
    checks = [
        {"key": "w", "status": "warn", "title": "W", "detail": "", "fact_ids": [1]},
        {"key": "f", "status": "fail", "title": "F", "detail": "", "fact_ids": [2]},
        {"key": "p", "status": "pass", "title": "P", "detail": "", "fact_ids": []},
    ]
    assert [p["vars"]["title"] for p in run([], checks)] == ["F", "W"]


def test_flag_on_a_line_not_added_is_low():
    ev = [
        {
            "fact_id": 4,
            "confidence": 1.0,
            "status": "extracted",
            "review": {"status": "needs_review", "reasons": ["engines_disagree"]},
        }
    ]
    (p,) = run([atom("m", role="not_a_paid_cost", measurement="maximum", evidence=ev)])
    assert (p["kind"], p["severity"], p["fact_ids"]) == ("extraction_flag", "low", [4])


def test_unused_fee_mentions_grouped_per_document():
    mentions = [{"fact_id": i, "filename": f} for i, f in ((1, "a.pdf"), (2, "a.pdf"), (3, "b.pdf"))]
    pts = review_points(
        {"current": {"total_known": "0", "atoms": []}, "aum": {}, "checks": [], "unused_mentions": mentions}
    )
    assert sorted((p["vars"]["file"], p["fact_ids"]) for p in pts) == [("a.pdf", [1, 2]), ("b.pdf", [3])]
    assert all(p["kind"] == "unused_mentions" and p["amount"] is None for p in pts)
