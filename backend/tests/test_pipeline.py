"""Golden-label tests: the synthetic documents are generated from demo/spec.py, so every value the
pipeline extracts can be compared with the truth. Also covers the master-prompt acceptance gates."""

import importlib.util
from decimal import Decimal as Dec
from pathlib import Path

import pytest

from pce.demo import spec as S
from pce.demo.generate import generate
from pce.demo.offline import load_folder, run
from pce.extraction import layout
from pce.extraction.parsers import extract

pytestmark = pytest.mark.ocr  # the corpus includes a scanned statement read with Tesseract


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("synthetic")
    generate(out)
    return out


@pytest.fixture(scope="module")
def result(corpus):
    return run(corpus)


def test_every_document_classified(corpus):
    docs, _ = load_folder(corpus)
    types = {d["filename"]: d["doc_type"] for d in docs}
    assert "unknown" not in types.values()
    assert types["alpha_estratto_conto_Q3_2026_scan.pdf"] == "cash_statement"
    assert types["beta_europe_price_schedule_2026.pdf"] == "tariff"


def test_positions_match_golden_labels_with_evidence(corpus):
    _docs, facts = load_folder(corpus)
    pos = {f["isin"]: f for f in facts if f["kind"] == "position" and f["isin"]}
    for p in S.ALPHA_POSITIONS + S.BETA_POSITIONS:
        if p.isin:
            assert Dec(pos[p.isin]["value"]) == p.value_chf, p.isin
    alpha = pos["ZZGEQLDRA013"]["evidence"]
    assert alpha["page"] == 2 and len(alpha["bbox"]) == 4 and alpha["bbox"][0] < alpha["bbox"][2]
    beta = pos["ZZUSGRI00019"]["evidence"]
    assert beta["sheet"] == "Holdings" and beta["cell"] == "H8"


@pytest.mark.parametrize("engine", layout.OCR_ENGINES)
def test_scanned_statement_read_by_ocr(corpus, engine, monkeypatch):
    """Both scan readers (Tesseract, RapidOCR when its extra is installed, SC-5.22) read the same debits."""
    if engine == "rapidocr" and importlib.util.find_spec("rapidocr") is None:
        pytest.skip("rapidocr extra not installed")
    monkeypatch.setattr(layout, "ocr_engine", lambda: engine)
    res, pages = extract("scan.pdf", (corpus / "alpha_estratto_conto_Q3_2026_scan.pdf").read_bytes())
    assert pages[0].engine == engine
    assert any("read with OCR" in w for w in res.profile.warnings)
    debits = {f.fee_code: Dec(f.value) for f in res.facts if f.kind == "cash_debit"}
    assert debits == {"ADVISORY_FEE": Dec("6400.00"), "CUSTODY_FEE": Dec("1500.00")}


def test_kid_amf_included_in_ocf(result):
    atoms = {a["id"]: a for a in result["current"]["atoms"]}
    ocf = next(
        a for a in atoms.values() if a["instrument_id"] == "ZZGEQLDRA013" and a["fee_code"] == "FUND_ONGOING"
    )
    amf = next(
        a for a in atoms.values() if a["instrument_id"] == "ZZGEQLDRA013" and a["fee_code"] == "FUND_MGMT_FEE"
    )
    assert Dec(ocf["amount"]) == Dec("9720.00")  # 900'000 × 1.08 %
    assert amf["role"] == "included_in_parent" and amf["included_in"] == ocf["id"]


def test_missing_cost_report_creates_request_not_zero(result):
    beta = [
        a
        for a in result["current"]["atoms"]
        if a["institution"] == "Bank Beta (Synthetic)" and a["layer"] in ("L1", "L2", "L3")
    ]
    assert beta and all(a["measurement"] == "unknown" and a["amount"] is None for a in beta)
    assert not result["current"]["is_complete"]
    assert any(
        r["key"] == "cost_report:Bank Beta (Synthetic)" and r["priority"] == 1 for r in result["requests"]
    )


def test_luxembourg_tariff_rejected_for_swiss_booking(result):
    chk = [c for c in result["checks"] if "price schedule rejected" in c["title"]]
    assert chk and chk[0]["status"] == "fail" and "LU" in chk[0]["detail"]
    assert not any("0.30" in (a["formula"] or "") for a in result["current"]["atoms"])


def test_kid_illustrations_and_maxima_not_counted(result):
    for a in result["current"]["atoms"]:
        if a["measurement"] in ("illustrative", "maximum"):
            assert a["role"] == "not_a_paid_cost"


def test_cash_debits_counted_once(result):
    adv = [
        a
        for a in result["current"]["atoms"]
        if a["fee_code"] == "ADVISORY_FEE" and a["institution"] == "Bank Alpha (Synthetic)"
    ]
    assert sorted(a["role"] for a in adv) == ["corroborating", "counted"]


def test_current_totals(result):
    cur = result["current"]
    # Alpha service 40,159.60 observed (incl. VAT 8.1% on advisory + custody = 2,559.60)
    # + product estimates 21,290 (KID rates × holdings)
    assert Dec(cur["billed_known"]) == Dec("40159.60")
    assert Dec(cur["embedded_known"]) == Dec("21290.00")
    assert Dec(cur["total_known"]) == Dec("61449.60")


def test_scenarios(result):
    same = result["scenarios"]["same_holdings"]["comparison"]
    opt = result["scenarios"]["optimized"]["comparison"]
    assert same["bound"] == "at_least" and same["like_for_like"]
    assert Dec(same["current_known"]) == Dec("60839.60")  # stamp duty excluded from comparison
    assert Dec(same["proposal_known"]) == Dec(
        "54319.50"
    )  # EAM 25,500 + custody 4,000 + 830 + 310 + VAT 2,389.50 + products 21,290
    assert Dec(same["annual_saving"]) == Dec("6520.10")
    assert Dec(same["payback_months"]) == Dec("2.8")
    assert not opt["like_for_like"] and Dec(opt["annual_saving"]) == Dec("14700.10")


def test_vat_depends_on_domicile(corpus):
    from pce.analysis import analyse

    docs, facts = load_folder(corpus)
    abroad = analyse({"domicile": "IT"}, docs, facts, S.PROPOSAL_DEFAULTS)
    assert not any(
        a["fee_code"] == "VAT_ON_FEES" for a in abroad["scenarios"]["same_holdings"]["ledger"]["atoms"]
    )


def test_internal_verdict_blocked_by_missing_evidence(result):
    assert result["internal"]["verdict"] == "insufficient_evidence"


def test_rejected_fact_is_excluded(corpus):
    from pce.analysis import analyse

    docs, facts = load_folder(corpus)
    for f in facts:
        if f["kind"] == "fee_observed" and f["fee_code"] == "FX_COMMISSION":
            f["status"] = "rejected"
    r = analyse({"domicile": "CH"}, docs, facts, S.PROPOSAL_DEFAULTS)
    assert Dec(r["current"]["billed_known"]) == Dec("40159.60") - Dec("1240.00")
