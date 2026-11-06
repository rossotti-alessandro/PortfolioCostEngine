from datetime import date
from decimal import Decimal as Dec

import pytest

from pce.engine.isin import find_isins, is_synthetic, is_valid_isin, make_synthetic_isin
from pce.engine.ledger import FeeAtom, Incidence, Layer, Measurement, aggregate
from pce.engine.money import D, parse_amount
from pce.engine.scenarios import (
    Bound,
    HoldingInput,
    ProductRate,
    compare,
    internal_economics,
    product_atoms,
)
from pce.engine.tariff import (
    FeeRule,
    Tariff,
    TierMethod,
    annualize,
    bps_fee,
    marginal_tier_fee,
    prorate,
    whole_base_tier_fee,
)

O, E, C, U = Measurement.OBSERVED, Measurement.ESTIMATED, Measurement.CONTRACTUAL, Measurement.UNKNOWN
B, EM = Incidence.BILLED, Incidence.EMBEDDED


def atom(aid, amount, meas=O, inc=B, layer=Layer.CUSTODY, **kw):
    ev = kw.pop("evidence_ids", ("ev1",) if meas == O else ())
    return FeeAtom(aid, kw.pop("code", aid), layer, kw.pop("label", aid), kw.pop("inst", "Bank A"),
                   None if amount is None else D(amount), meas, inc, evidence_ids=ev, **kw)


# ---------- money / parsing ----------
def test_floats_rejected():
    with pytest.raises(TypeError):
        D(0.1)


@pytest.mark.parametrize("raw,expected", [
    ("1'234'567.89", "1234567.89"), ("1’234.50", "1234.50"), ("1.234.567,89", "1234567.89"),
    ("1,234,567.89", "1234567.89"), ("-1 234,50", "-1234.50"), ("1'200.00-", "-1200.00"),
    ("(350.00)", "-350.00"), ("CHF 18'000.00", "18000.00"), ("0.125", "0.125"),
])
def test_parse_amount_locales(raw, expected):
    assert parse_amount(raw) == Dec(expected)


@pytest.mark.parametrize("raw", ["1.200", "1,200"])
def test_parse_amount_ambiguous_rejected(raw):
    with pytest.raises(ValueError):
        parse_amount(raw)


# ---------- ISIN ----------
def test_isin_checksum_real_examples():
    assert is_valid_isin("US0378331005")  # Apple Inc.
    assert is_valid_isin("LU0329592298")  # share class cited in the kit audit
    assert not is_valid_isin("US0378331006")


def test_synthetic_isin_is_valid_and_flagged():
    code = make_synthetic_isin("GEQ000001")
    assert is_valid_isin(code) and is_synthetic(code)
    assert find_isins(f"Fund A {code} 1'000") == [code]


# ---------- tariff math ----------
def test_bps_and_caps():
    assert bps_fee("4000000", 45) == Dec("18000")
    assert bps_fee("10000", 10, minimum=100) == Dec("100")
    assert bps_fee("500000", 50, maximum=1000) == Dec("1000")
    with pytest.raises(ValueError):
        bps_fee("1000", 10, minimum=500, maximum=100)


def test_marginal_vs_whole_base_tiers_differ():
    tiers = [(1_000_000, 60), (None, 40)]
    assert marginal_tier_fee(2_000_000, tiers) == Dec("10000")
    assert whole_base_tier_fee(2_000_000, tiers) == Dec("8000")
    assert marginal_tier_fee(500_000, tiers) == Dec("3000")


def test_tiers_must_be_ascending():
    with pytest.raises(ValueError):
        marginal_tier_fee(1, [(2_000_000, 50), (1_000_000, 40), (None, 30)])


def test_rule_minimum_with_tiers():
    r = FeeRule("CUSTODY_FEE", "Custody", "custody_eligible", tiers=[(None, 10)], minimum=1000)
    assert r.annual_amount(200_000) == Dec("1000")


def test_proration_and_annualization():
    assert prorate(36500, 30) == Dec("3000")
    assert annualize(Dec("4275"), 91) == Dec("4275") * 365 / 91
    with pytest.raises(ValueError):
        prorate(100, 400)


def test_jurisdiction_mismatch_rejected():
    lux = Tariff("JB-LUX", "Bank (LU entity)", "LU", date(2026, 1, 1), None, "EUR", ())
    ok, reason = lux.applicability("CH", date(2026, 6, 30))
    assert not ok and "LU" in reason and "CH" in reason


def test_stale_tariff_rejected():
    old = Tariff("T", "Bank", "CH", date(2020, 1, 1), date(2022, 12, 31), "CHF", ())
    ok, reason = old.applicability("CH", date(2026, 6, 30))
    assert not ok and "not in force" in reason


# ---------- ledger rules ----------
def test_amf_inside_ocf_counts_ocf_only():
    # Kit acceptance: OCF 1.08% with AMF 0.75% included -> 1.08%, never 1.83%
    h = HoldingInput("LU0329592298", "Fund", "FUND", Dec("1000000"), "Bank A", "A1")
    rates = [ProductRate("LU0329592298", "FUND_ONGOING", Dec("1.08")),
             ProductRate("LU0329592298", "FUND_MGMT_FEE", Dec("0.75"), included_in_code="FUND_ONGOING")]
    s = aggregate(product_atoms([h], rates, "cur"), scope_aum=Dec("1000000"))
    assert s.total_known == Dec("10800")
    assert s.total_bps == Dec("108.0")
    assert s.embedded_known == Dec("10800") and s.billed_known == 0


def test_all_in_fee_custody_not_added():
    allin = atom("ALLIN", "20000", layer=Layer.SERVICE)
    cust = atom("CUST", "5000", included_in="ALLIN")
    assert aggregate([allin, cust]).total_known == Dec("20000")


def test_custody_exclusive_is_added():
    assert aggregate([atom("MGMT", "20000", layer=Layer.SERVICE), atom("CUST", "5000")]).total_known == Dec("25000")


def test_fee_report_and_cash_debit_counted_once_and_mismatch_flagged():
    report = atom("REPORT_CUST", "5700")
    debit_ok = atom("DEBIT_CUST", "5700", corroborates="REPORT_CUST")
    s = aggregate([report, debit_ok])
    assert s.total_known == Dec("5700") and not s.warnings
    debit_bad = atom("DEBIT_CUST", "6500", corroborates="REPORT_CUST")
    s2 = aggregate([report, debit_bad])
    assert s2.total_known == Dec("5700") and s2.warnings


def test_missing_is_not_zero():
    s = aggregate([atom("MGMT", "17100", layer=Layer.SERVICE), atom("FX", None, meas=U, layer=Layer.TRADING)])
    assert s.total_known == Dec("17100")
    assert not s.is_complete
    assert [a.atom_id for a in s.unknown] == ["FX"]


def test_unknown_with_amount_is_rejected():
    with pytest.raises(ValueError):
        atom("X", "10", meas=U)


def test_observed_requires_evidence():
    with pytest.raises(ValueError):
        atom("X", "10", meas=O, evidence_ids=())


def test_kid_illustrative_and_maximum_never_counted():
    s = aggregate([
        atom("OCF", "5400", meas=E, inc=EM, layer=Layer.PRODUCT),
        atom("KID_EXAMPLE", "300", meas=Measurement.ILLUSTRATIVE, inc=EM, layer=Layer.PRODUCT),
        atom("ENTRY_MAX", "3000", meas=Measurement.MAXIMUM, inc=B, layer=Layer.PRODUCT, recurring=False),
    ])
    assert s.total_known == Dec("5400") and s.one_off_known == 0


def test_insurance_wrapper_layering_is_additive():
    s = aggregate([
        atom("WRAP", "4000", meas=E, inc=EM, layer=Layer.PRODUCT),
        atom("UNDERLYING_OCF", "6000", meas=E, inc=EM, layer=Layer.PRODUCT),
    ])
    assert s.total_known == Dec("10000")


def test_multi_bank_split():
    s = aggregate([atom("A", "100", inst="Bank A"), atom("B", "250", inst="Bank B")])
    assert s.by_institution == {"Bank A": Dec("100"), "Bank B": Dec("250")}


def test_graph_errors():
    with pytest.raises(ValueError):
        aggregate([atom("A", "1", included_in="MISSING")])
    with pytest.raises(ValueError):
        aggregate([atom("A", "1", corroborates="B"), atom("B", "1", corroborates="A")])
    with pytest.raises(ValueError):
        aggregate([atom("A", "1"), atom("A", "2")])


def test_import_is_idempotent_by_atom_id():
    a = [atom("A", "100"), atom("B", "50")]
    assert aggregate(a).total_known == aggregate(list(a)).total_known


# ---------- scenarios ----------
def _summary(total, complete=True, aum="4000000"):
    atoms = [atom("K", total, layer=Layer.SERVICE)]
    if not complete:
        atoms.append(atom("U", None, meas=U))
    return aggregate(atoms, scope_aum=Dec(aum))


def test_kit_regression_figures():
    # The kit's reference numbers, recomputed (CRITICAL_REVIEW #4: fixture only, not demo data)
    same = compare(_summary("38100"), _summary("32540"), 8000)
    opt = compare(_summary("38100"), _summary("23740"), 8000, like_for_like=False)
    assert same.annual_saving == Dec("5560") and same.first_year_net == Dec("-2440")
    assert opt.annual_saving == Dec("14360") and opt.first_year_net == Dec("6360")
    assert same.payback_months == Dec("17.3")
    assert not opt.like_for_like and any("not a like-for-like" in c for c in opt.caveats)


def test_negative_saving_has_no_payback():
    c = compare(_summary("1000"), _summary("1200"), 200)
    assert c.payback_months is None and c.annual_saving == Dec("-200")


def test_saving_bounds_follow_completeness():
    assert compare(_summary("100", False), _summary("50")).bound == Bound.LOWER
    assert compare(_summary("100"), _summary("50", False)).bound == Bound.UPPER
    assert compare(_summary("100", False), _summary("50", False)).bound == Bound.INDETERMINATE
    assert compare(_summary("100"), _summary("50")).bound == Bound.POINT


def test_switched_products_change_product_cost():
    h_old = HoldingInput("ZZOLD", "Active fund", "FUND", Dec("1000000"), "Bank A", "A1")
    h_new = HoldingInput("ZZNEW", "Index ETF", "ETF", Dec("1000000"), "New", "N1")
    cur = aggregate(product_atoms([h_old], [ProductRate("ZZOLD", "FUND_ONGOING", Dec("1.65"))], "c"))
    new = aggregate(product_atoms([h_new], [ProductRate("ZZNEW", "FUND_ONGOING", Dec("0.12"))], "p"))
    assert cur.total_known - new.total_known == Dec("15300")


def test_internal_economics_blocks_on_missing_evidence():
    cmp_ = compare(_summary("38000", False), _summary("30000"), 5000)
    rev = [atom("REV", "24000", meas=C, layer=Layer.SERVICE)]
    ie = internal_economics(rev, 9000, 6000, cmp_, evidence_complete=False)
    assert ie.verdict == "insufficient_evidence"
    assert ie.annual_contribution == Dec("15000") and ie.first_year_contribution == Dec("9000")
    ie2 = internal_economics(rev, 9000, 6000, compare(_summary("38000"), _summary("30000")), evidence_complete=True)
    assert ie2.verdict == "proceed_to_senior_review"
