"""SC-5.14: agentic revalidation graph. SYNTHETIC facts only, no model, no disk."""

from __future__ import annotations

from pce.extraction.models import Evidence, Fact, Review
from pce.extraction.revalidate import (
    BACKEND_CHECKS,
    Opinion,
    Specialists,
    Verdict,
    reconcile_kid_pct,
    reconcile_totals,
    revalidate,
)


def fact(label: str, value: str, box: list[float], reasons: list[str] | None = None, field: str = "amount",
         snippet: str = "") -> Fact:  # fmt: skip
    return Fact(
        key=f"{label}:{value}:{box[1]}",
        kind="fee_mention",
        field=field,
        label=label,
        value=value,
        evidence=Evidence(page=1, bbox=box, snippet=snippet or label, engine="pdfplumber-text"),
        review=Review(status="needs_review" if reasons else "accepted", reasons=reasons or []),
    )


def frozen(f: Fact) -> tuple:
    return f.value, f.label, f.evidence.bbox, f.evidence.page


def confirm(name: str):
    return lambda f: Opinion(name, Verdict.CONFIRM, "same value here")


def flag(name: str):
    return lambda facts: {i: Opinion(name, Verdict.FLAG, "not a fee") for i in range(len(facts))}


def test_reader_confirmation_clears_a_reading_doubt_and_stops_escalating():
    calls: list[str] = []

    def slow(f):
        calls.append("slow")
        return Opinion("slow", Verdict.CONFIRM)

    f = fact("Custody fee", "0.25", [300, 100, 330, 110], ["engines_disagree"], "rate_pct")
    [out] = revalidate([f], Specialists(readers=[confirm("rapidocr"), slow]))
    assert out.review.status == "accepted"
    assert "rapidocr" in out.review.engines
    assert calls == []  # the cheaper reader agreed: the slow one never ran
    assert out.extra["revalidation_path"] == ["triage", "readers", "decide"]


def test_unresolved_doubt_stays_in_review():
    f = fact("Custody fee", "0.25", [300, 100, 330, 110], ["not_confirmed"], "rate_pct")
    abstain = lambda f: Opinion("rapidocr", Verdict.ABSTAIN, "nothing read")  # noqa: E731
    [out] = revalidate([f], Specialists(readers=[abstain]))
    assert out.review.status == "needs_review"
    assert out.review.reasons == ["not_confirmed"]


def test_rule_doubts_are_not_cleared_by_a_reader():
    f = fact(
        "Management fee", "4.5", [300, 100, 330, 110], ["engines_disagree", "rate_out_of_range"], "rate_pct"
    )
    [out] = revalidate([f], Specialists(readers=[confirm("rapidocr")]))
    assert out.review.reasons == ["rate_out_of_range"]
    assert out.review.status == "needs_review"


def test_critic_only_flags_never_drops_and_never_changes_values():
    facts = [
        fact("Custody fee", "0.25", [300, 100, 330, 110], field="rate_pct"),
        fact("Brokerage", "125", [300, 120, 330, 130]),
    ]
    before = [frozen(f) for f in facts]
    out = revalidate(facts, Specialists(critic=flag("critic")))
    assert [frozen(f) for f in out] == before
    assert all(f.review.status == "needs_review" and "flagged_by_critic" in f.review.reasons for f in out)


def test_critic_cannot_confirm_away_a_doubt():
    f = fact("Custody fee", "0.25", [300, 100, 330, 110], ["not_confirmed"], "rate_pct")
    critic = lambda facts: {0: Opinion("critic", Verdict.CONFIRM)}  # noqa: E731
    [out] = revalidate([f], Specialists(critic=critic))
    assert out.review.status == "needs_review"  # the critic judges meaning, never the reading
    assert frozen(out) == frozen(f)


def test_totals_reconcile_confirm_rows_and_clear_separator_doubt():
    facts = [
        fact("Custody fee", "1.250", [400, 100, 440, 110], ["separator_ambiguous"]),
        fact("Brokerage", "300", [400, 115, 440, 125]),
        fact("Total costs", "1550", [400, 130, 440, 140], ["not_confirmed"]),
    ]
    facts[0].value = "1250"  # the finder's reading of "1.250"; the sum proves the separator
    ops = reconcile_totals(facts)
    assert set(ops) == {0, 1, 2}
    out = revalidate(facts, Specialists(checks=BACKEND_CHECKS))
    assert [f.review.status for f in out] == ["accepted", "accepted", "accepted"]


def test_totals_that_do_not_add_up_confirm_nothing():
    facts = [
        fact("Custody fee", "1250", [400, 100, 440, 110]),
        fact("Brokerage", "300", [400, 115, 440, 125]),
        fact("Total costs", "1560", [400, 130, 440, 140], ["not_confirmed"]),
    ]
    assert reconcile_totals(facts) == {}
    assert revalidate(facts, Specialists(checks=BACKEND_CHECKS))[2].review.status == "needs_review"


def test_kid_amount_and_percent_on_10000_confirm_each_other():
    s = "SYNTHETIC KID. Example investment 10 000 EUR"
    facts = [
        fact("Entry costs", "150", [300, 200, 340, 210], ["not_confirmed"], snippet=s),
        fact("Entry costs", "1.5", [400, 200, 430, 210], ["not_confirmed"], "rate_pct", snippet=s),
        fact("Exit costs", "50", [300, 220, 340, 230], ["not_confirmed"], snippet=s),
        fact("Exit costs", "0.6", [400, 220, 430, 230], ["not_confirmed"], "rate_pct", snippet=s),
    ]
    assert set(reconcile_kid_pct(facts)) == {0, 1}  # 50 on 10 000 is 0.5 %, not 0.6 %
    out = revalidate(facts, Specialists(checks=BACKEND_CHECKS))
    assert [f.review.status for f in out] == ["accepted", "accepted", "needs_review", "needs_review"]


def test_no_specialists_leaves_review_as_verify_set_it():
    facts = [
        fact("Custody fee", "0.25", [300, 100, 330, 110], field="rate_pct"),
        fact("Brokerage", "125", [300, 120, 330, 130], ["engines_disagree"]),
    ]
    out = revalidate([f.model_copy(deep=True) for f in facts], Specialists())
    assert [(f.review.status, f.review.reasons) for f in out] == [
        (f.review.status, f.review.reasons) for f in facts
    ]


def _schedule(tmp_path):
    from conftest import write_text_pdf

    pdf = tmp_path / "synthetic_cost_report.pdf"
    write_text_pdf(
        pdf,
        [
            (50, 780, 12, "SYNTHETIC Bank - Costs and charges 2026"),
            (50, 740, 10, "Costs and charges"),
            (300, 740, 9, "CHF"),
            (50, 720, 9, "Custody fee"),
            (300, 720, 9, "1'250.00"),
            (50, 708, 9, "Brokerage fees"),
            (300, 708, 9, "300.00"),
            (50, 696, 9, "Total costs"),
            (300, 696, 9, "1'550.00"),
        ],
    )
    return pdf


def test_app_extract_unchanged_when_revalidation_is_off(tmp_path, monkeypatch):
    from pce.extraction.parsers import extract

    pdf = _schedule(tmp_path)
    monkeypatch.delenv("PCE_REVALIDATE", raising=False)
    res, _ = extract(pdf.name, pdf.read_bytes())
    checks = [c.name for f in res.facts if f.review for c in f.review.checks]
    assert checks and not any(c.startswith("revalidate:") for c in checks)


def test_app_extract_runs_page_arithmetic_when_on(tmp_path, monkeypatch):
    from pce.extraction.parsers import extract

    pdf = _schedule(tmp_path)
    monkeypatch.setenv("PCE_REVALIDATE", "1")
    res, _ = extract(pdf.name, pdf.read_bytes())
    fees = [f for f in res.facts if f.label in ("Custody fee", "Brokerage fees")]
    assert len(fees) == 2
    assert all(
        any(c.name == "revalidate:reconcile_totals" and c.passed for c in f.review.checks) for f in fees
    )
