"""SC-7.21: end-to-end cost edge cases through analyse(). All data here is SYNTHETIC.

One small pack per case: a CHF statement at one bank plus whatever the case needs. The matrix pins how every
asset class, currency, report period, duplicate and product document is costed, and the ledger invariants
that must hold whatever the input: no negative cost, unknown never zero, the total is the sum of counted
atoms, and hidden costs never move it.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pce.analysis import analyse
from pce.demo.spec import PROPOSAL_DEFAULTS

BANK = "Synthetic Bank SA"
NESTLE = "CH0038863350"
CONF_BOND = "CH0224397213"
ETF = "IE00B4L5Y983"
ETF_USD = "IE00B5BMR087"
SP = "CH1234567894"
FUND_A = "LU0274208692"  # share class A
FUND_B = "LU0274209740"  # share class B of the same fund


def doc(i: int, t: str, **profile: str) -> dict:
    return {"id": i, "filename": f"doc{i}-SYNTHETIC.pdf", "doc_type": t, "profile": profile}


STATEMENT = doc(1, "portfolio_statement", institution=BANK, jurisdiction="CH", as_of="2026-09-30")


def report(i: int = 2, ps: str = "2025-10-01", pe: str = "2026-09-30") -> dict:
    return doc(i, "cost_report", institution=BANK, jurisdiction="CH", period_start=ps, period_end=pe)


def cash_statement(i: int = 4, ps: str = "2026-01-01", pe: str = "2026-12-31") -> dict:
    return doc(i, "cash_statement", institution=BANK, period_start=ps, period_end=pe)


def pos(i: int, label: str, value: str, ccy: str = "CHF", isin: str | None = None, **extra: str) -> dict:
    return {
        "id": i,
        "document_id": 1,
        "key": f"p{i}",
        "kind": "position",
        "field": "market_value",
        "label": label,
        "value": value,
        "currency": ccy,
        "isin": isin,
        "fee_code": None,
        "measurement": None,
        "status": "extracted",
        "extra": extra,
    }


def fee(i: int, code: str, value: str, ccy: str = "CHF", doc_id: int = 2, kind: str = "fee_observed") -> dict:
    return {
        "id": i,
        "document_id": doc_id,
        "key": f"f{i}",
        "kind": kind,
        "field": "annual_amount",
        "label": code.replace("_", " ").lower(),
        "value": value,
        "currency": ccy,
        "isin": None,
        "fee_code": code,
        "measurement": "observed",
        "status": "extracted",
        "extra": {},
    }


def fx(i: int, pair: str, rate: str) -> dict:
    return {
        "id": i,
        "document_id": 1,
        "key": f"fx{i}",
        "kind": "meta",
        "field": "fx_rate",
        "label": pair,
        "value": rate,
        "currency": None,
        "isin": None,
        "fee_code": None,
        "measurement": None,
        "status": "extracted",
        "extra": {},
    }


def rate(
    i: int, doc_id: int, isin: str, code: str, pct: str | None, meas: str = "estimated", **extra: str
) -> dict:
    return {
        "id": i,
        "document_id": doc_id,
        "key": f"r{i}",
        "kind": "product_cost",
        "field": "rate_pct",
        "label": code,
        "value": pct,
        "currency": None,
        "isin": isin,
        "fee_code": code,
        "measurement": meas,
        "status": "extracted",
        "extra": extra,
    }


# Service, custody and trading observed, so only the case under test can leave the view incomplete.
BANK_FEES = [
    fee(10, "MGMT_DISCRETIONARY", "800"),
    fee(11, "CUSTODY_FEE", "1000"),
    fee(12, "BROKERAGE", "100"),
]


def run(docs: list[dict], facts: list[dict]) -> dict:
    return analyse({"domicile": "CH"}, docs, facts, PROPOSAL_DEFAULTS)


def atoms(r: dict, **match: object) -> list[dict]:
    return [a for a in r["current"]["atoms"] if all(a.get(k) == v for k, v in match.items())]


def check(r: dict, prefix: str) -> dict | None:
    return next((c for c in r["checks"] if c["key"].startswith(prefix)), None)


def assert_invariants(r: dict) -> None:
    """Hold for every pack: the total is what the ledger counts; nothing negative, no unknown as 0."""
    cur = r["current"]
    counted = [Decimal(a["amount"]) for a in cur["atoms"] if a["role"] == "counted"]
    assert Decimal(cur["total_known"]) == sum(counted, Decimal(0))
    assert all(v >= 0 for v in counted), "a counted cost is negative"
    for a in cur["atoms"]:
        if a["role"] == "unknown":
            assert a["amount"] is None
    if any(a["role"] == "unknown" and a["materiality"] == "material" for a in cur["atoms"]):
        assert cur["is_complete"] is False


# ------------------------------------------------------------------ report periods


def test_twelve_month_report_counts_as_printed() -> None:
    r = run([STATEMENT, report()], [pos(1, "Nestle SA", "100000", isin=NESTLE), *BANK_FEES])
    assert r["current"]["total_known"] == "1900.00"
    assert r["current"]["is_complete"] is True
    assert check(r, "period:") is None
    assert_invariants(r)


def test_six_month_report_is_annualised_by_days() -> None:
    half = [fee(10, "MGMT_DISCRETIONARY", "400"), fee(11, "CUSTODY_FEE", "500"), fee(12, "BROKERAGE", "50")]
    r = run(
        [STATEMENT, report(ps="2026-04-01", pe="2026-09-30")],
        [pos(1, "Nestle SA", "100000", isin=NESTLE), *half],
    )
    [custody] = atoms(r, fee_code="CUSTODY_FEE")
    assert Decimal(custody["amount"]) == (Decimal(500) * 365 / 183).quantize(Decimal("0.01"))
    assert check(r, "period:2")["status"] == "warn"
    assert_invariants(r)


def test_reversed_report_period_is_not_annualised() -> None:
    """End before start (an extraction slip) used to annualise by -181 days: every fee turned negative."""
    r = run(
        [STATEMENT, report(ps="2026-09-30", pe="2026-04-01")],
        [pos(1, "Nestle SA", "100000", isin=NESTLE), *BANK_FEES],
    )
    assert r["current"]["total_known"] == "1900.00"
    assert check(r, "period:2")["status"] == "fail"
    assert_invariants(r)


def test_report_of_a_few_days_is_a_lower_bound_not_annualised() -> None:
    """A 1-day report × 365 turned CHF 1'900 of fees into CHF 693'500."""
    r = run(
        [STATEMENT, report(ps="2026-09-30", pe="2026-09-30")],
        [pos(1, "Nestle SA", "100000", isin=NESTLE), *BANK_FEES],
    )
    assert r["current"]["total_known"] == "1900.00"
    c = check(r, "period:2")
    assert c["status"] == "warn" and "lower bound" in c["detail"]
    assert_invariants(r)


def test_partial_cash_debits_are_annualised_by_days_covered() -> None:
    q = [fee(30, "CUSTODY_FEE", "250", doc_id=4, kind="cash_debit")]
    r = run(
        [STATEMENT, report(), cash_statement(ps="2026-07-01", pe="2026-09-29")],
        [pos(1, "Nestle SA", "100000", isin=NESTLE), BANK_FEES[0], BANK_FEES[2], *q],
    )
    [custody] = atoms(r, fee_code="CUSTODY_FEE")
    assert Decimal(custody["amount"]) == (Decimal(250) * 365 / 91).quantize(Decimal("0.01"))
    assert custody["measurement"] == "estimated"
    assert_invariants(r)


# ------------------------------------------------------------------ negative and unconverted fee lines


def test_negative_fee_total_in_a_report_is_unknown_not_a_saving() -> None:
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        BANK_FEES[0],
        fee(11, "CUSTODY_FEE", "-1000"),
        BANK_FEES[2],
    ]
    r = run([STATEMENT, report()], facts)
    assert r["current"]["total_known"] == "900.00"
    [custody] = atoms(r, fee_code="CUSTODY_FEE")
    assert custody["role"] == "unknown"
    assert check(r, "negative_fee:")["status"] == "fail"
    assert_invariants(r)


def test_refund_line_inside_a_positive_fee_is_netted() -> None:
    """A partial refund on one line is part of what the client paid that year: lines are summed."""
    facts = [pos(1, "Nestle SA", "100000", isin=NESTLE), *BANK_FEES, fee(13, "CUSTODY_FEE", "-200")]
    r = run([STATEMENT, report()], facts)
    [custody] = atoms(r, fee_code="CUSTODY_FEE")
    assert custody["amount"] == "800.00" and custody["role"] == "counted"
    assert check(r, "negative_fee:") is None


def test_negative_cash_debit_pool_is_unknown() -> None:
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        fee(30, "CUSTODY_FEE", "-250", doc_id=4, kind="cash_debit"),
    ]
    r = run([STATEMENT, cash_statement()], facts)
    [custody] = [a for a in atoms(r, fee_code="CUSTODY_FEE")]
    assert custody["role"] == "unknown"
    assert check(r, "negative_fee:")["status"] == "fail"
    assert_invariants(r)


def test_fee_in_a_currency_without_printed_rate_is_unknown_not_dropped() -> None:
    """A USD performance fee with no USD/CHF rate used to vanish while the view said complete."""
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        *BANK_FEES,
        fee(13, "PERFORMANCE_FEE_MANDATE", "500", "USD"),
    ]
    r = run([STATEMENT, report()], facts)
    [perf] = atoms(r, fee_code="PERFORMANCE_FEE_MANDATE")
    assert perf["role"] == "unknown" and perf["amount"] is None
    assert r["current"]["is_complete"] is False
    assert check(r, "fx_missing:")["status"] == "fail"
    assert_invariants(r)


def test_fee_in_a_foreign_currency_with_printed_rate_is_converted() -> None:
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        fx(5, "EUR/CHF", "0.94"),
        BANK_FEES[0],
        BANK_FEES[2],
        fee(11, "CUSTODY_FEE", "1000", "EUR"),
    ]
    r = run([STATEMENT, report()], facts)
    [custody] = atoms(r, fee_code="CUSTODY_FEE")
    assert custody["amount"] == "940.00"
    assert check(r, "fx:")["status"] == "info"
    assert_invariants(r)


# ------------------------------------------------------------------ asset classes


KID, TERMSHEET = doc(3, "kid", as_of="2026-03-01"), doc(5, "termsheet", as_of="2026-01-15")


@pytest.mark.parametrize(
    ("holding", "product_docs", "expect"),
    [
        (pos(1, "Nestle SA registered", "100000", isin=NESTLE), [], "none"),
        (pos(1, "Confederation 1.5% 2030", "100000", isin=CONF_BOND, asset_class="BOND"), [], "none"),
        (pos(1, "Call option SMI Dec26", "100000", asset_class="DERIVATIVE"), [], "none"),
        (pos(1, "Gold bars 1kg", "100000", asset_class="COMMODITY"), [], "none"),
        (pos(1, "Current account CHF", "100000", asset_class="CASH"), [], "none"),
        (pos(1, "World Equity UCITS ETF", "100000", isin=ETF), [], "unknown"),
        (pos(1, "Global Bond Fund A", "100000", isin=FUND_A), [], "unknown"),
        (pos(1, "Fund without ISIN", "100000", asset_class="FUND"), [], "unknown"),
        (pos(1, "Barrier Reverse Convertible on SMI", "100000", isin=SP), [], "unknown"),
        (pos(1, "Barrier Reverse Convertible on SMI", "100000"), [], "unknown"),
        (
            pos(1, "World Equity UCITS ETF", "100000", isin=ETF),
            [rate(40, 3, ETF, "FUND_ONGOING", "0.20"), rate(41, 3, ETF, "FUND_TRANSACTION", "0.05")],
            "250.00",
        ),
        (
            pos(1, "Barrier Reverse Convertible on SMI", "100000", isin=SP),
            [rate(40, 5, SP, "SP_ONGOING", "0.50"), rate(41, 5, SP, "SP_ENTRY_COST", "1.20")],
            "500.00",
        ),
    ],
    ids=[
        "equity",
        "direct-bond",
        "derivative",
        "commodity",
        "cash",
        "etf-no-kid",
        "fund-no-kid",
        "fund-no-isin",
        "structured-no-termsheet",
        "structured-no-isin",
        "etf-with-kid",
        "structured-with-termsheet",
    ],
)
def test_product_cost_by_asset_class(holding: dict, product_docs: list[dict], expect: str) -> None:
    docs = [STATEMENT, report(), KID, TERMSHEET]
    r = run(docs, [holding, *BANK_FEES, *product_docs])
    embedded = [
        a for a in r["current"]["atoms"] if a["layer"] in ("L4", "L5") and a["role"] != "not_a_paid_cost"
    ]
    if expect == "none":
        assert embedded == [] and r["current"]["is_complete"] is True
    elif expect == "unknown":
        assert [a["role"] for a in embedded] == ["unknown"]
        assert r["current"]["is_complete"] is False
        assert any(q["key"].startswith("kid:") for q in r["requests"])
    else:
        assert sum((Decimal(a["amount"]) for a in embedded if a["role"] == "counted"), Decimal(0)) == Decimal(
            expect
        )
        assert r["current"]["total_known"] == str(Decimal("1900.00") + Decimal(expect))
    assert_invariants(r)


def test_structured_entry_cost_is_one_off_not_annual() -> None:
    facts = [
        pos(1, "Barrier Reverse Convertible on SMI", "100000", isin=SP),
        *BANK_FEES,
        rate(40, 5, SP, "SP_ONGOING", "0.50"),
        rate(41, 5, SP, "SP_ENTRY_COST", "1.20"),
    ]
    r = run([STATEMENT, report(), TERMSHEET], facts)
    [entry] = atoms(r, fee_code="SP_ENTRY_COST")
    assert entry["role"] == "one_off" and entry["amount"] == "1200.00"
    assert r["current"]["one_off_known"] == "1200.00"


def test_kid_of_one_share_class_never_prices_another() -> None:
    facts = [
        pos(1, "Global Bond Fund A", "100000", isin=FUND_A),
        pos(2, "Global Bond Fund B", "50000", isin=FUND_B),
        *BANK_FEES,
        rate(40, 3, FUND_A, "FUND_ONGOING", "0.80"),
        rate(41, 3, FUND_A, "FUND_TRANSACTION", "0.10"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    a = {x["fee_code"]: x for x in atoms(r, instrument_id=FUND_A)}
    assert a["FUND_ONGOING"]["amount"] == "800.00"
    [b] = atoms(r, instrument_id=FUND_B)
    assert b["role"] == "unknown"
    assert_invariants(r)


def test_management_fee_inside_ongoing_charges_counts_once() -> None:
    facts = [
        pos(1, "Global Bond Fund A", "100000", isin=FUND_A),
        *BANK_FEES,
        rate(40, 3, FUND_A, "FUND_ONGOING", "1.08"),
        rate(41, 3, FUND_A, "FUND_MGMT_FEE", "0.75", included_in="FUND_ONGOING"),
        rate(42, 3, FUND_A, "FUND_TRANSACTION", "0.10"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    product = sum((Decimal(a["amount"]) for a in atoms(r, instrument_id=FUND_A, role="counted")), Decimal(0))
    assert product == Decimal("1180.00")  # 1.08% + 0.10%, not + 0.75%
    assert atoms(r, fee_code="FUND_MGMT_FEE")[0]["role"] == "included_in_parent"


def test_kid_without_transaction_costs_leaves_them_unknown() -> None:
    facts = [
        pos(1, "Global Bond Fund A", "100000", isin=FUND_A),
        *BANK_FEES,
        rate(40, 3, FUND_A, "FUND_ONGOING", "0.80"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    [tx] = atoms(r, fee_code="FUND_TRANSACTION")
    assert tx["role"] == "unknown"


# ------------------------------------------------------------------ performance fees


def test_fund_performance_fee_counts_on_top_of_ongoing_charges() -> None:
    facts = [
        pos(1, "Alpha Fund A", "100000", isin=FUND_A),
        *BANK_FEES,
        rate(40, 3, FUND_A, "FUND_ONGOING", "1.50"),
        rate(41, 3, FUND_A, "FUND_TRANSACTION", "0.10"),
        rate(42, 3, FUND_A, "FUND_PERFORMANCE", "0.40"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    [perf] = atoms(r, fee_code="FUND_PERFORMANCE")
    assert perf["role"] == "counted" and perf["amount"] == "400.00"
    assert r["current"]["total_known"] == "3900.00"


def test_zero_fund_performance_fee_adds_no_atom() -> None:
    facts = [
        pos(1, "Alpha Fund A", "100000", isin=FUND_A),
        *BANK_FEES,
        rate(40, 3, FUND_A, "FUND_ONGOING", "1.50"),
        rate(41, 3, FUND_A, "FUND_TRANSACTION", "0.10"),
        rate(42, 3, FUND_A, "FUND_PERFORMANCE", "0.00"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    assert atoms(r, fee_code="FUND_PERFORMANCE") == []


def test_mandate_performance_fee_is_a_service_cost() -> None:
    r = run(
        [STATEMENT, report()],
        [pos(1, "Nestle SA", "100000", isin=NESTLE), *BANK_FEES, fee(13, "PERFORMANCE_FEE_MANDATE", "2000")],
    )
    [perf] = atoms(r, fee_code="PERFORMANCE_FEE_MANDATE")
    assert perf["layer"] == "L1" and perf["role"] == "counted"
    assert r["current"]["total_known"] == "3900.00"


# ------------------------------------------------------------------ currencies and duplicates


def test_foreign_position_without_rate_is_unvalued_never_zero() -> None:
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        pos(2, "S&P 500 UCITS ETF", "50000", "USD", isin=ETF_USD),
        *BANK_FEES,
    ]
    r = run([STATEMENT, report()], facts)
    assert r["aum"]["total"] == "100000"
    [etf] = atoms(r, instrument_id=ETF_USD)
    assert etf["role"] == "unknown"
    assert check(r, "fx_missing:")["status"] == "fail"
    assert_invariants(r)


def test_foreign_fund_with_rate_is_costed_in_chf() -> None:
    facts = [
        pos(1, "World Equity UCITS ETF", "100000", "EUR", isin=ETF),
        fx(5, "EUR/CHF", "0.94"),
        *BANK_FEES,
        rate(40, 3, ETF, "FUND_ONGOING", "0.20"),
        rate(41, 3, ETF, "FUND_TRANSACTION", "0.05"),
    ]
    r = run([STATEMENT, report(), KID], facts)
    assert r["aum"]["total"] == "94000.00"
    [ocf] = atoms(r, fee_code="FUND_ONGOING")
    assert ocf["amount"] == "188.00"
    assert_invariants(r)


def test_same_cost_report_twice_counts_once() -> None:
    copy = report(i=6)
    facts = [
        pos(1, "Nestle SA", "100000", isin=NESTLE),
        *BANK_FEES,
        *[f | {"id": f["id"] + 100, "document_id": 6} for f in BANK_FEES],
    ]
    r = run([STATEMENT, report(), copy], facts)
    assert r["current"]["total_known"] == "1900.00"
    assert_invariants(r)


# ------------------------------------------------------------------ properties


_amount = st.decimals(min_value=Decimal("-5000"), max_value=Decimal("50000"), places=2, allow_nan=False)
_codes = st.sampled_from(["MGMT_DISCRETIONARY", "CUSTODY_FEE", "BROKERAGE", "VAT_ON_FEES", "TICKET_FEE"])


@settings(max_examples=60, deadline=None)
@given(
    lines=st.lists(st.tuples(_codes, _amount), min_size=1, max_size=8),
    days=st.integers(min_value=-400, max_value=400),
)
def test_any_report_keeps_the_ledger_invariants(lines: list[tuple[str, Decimal]], days: int) -> None:
    from datetime import date, timedelta

    end = date(2026, 9, 30)
    start = end - timedelta(days=days)
    facts = [pos(1, "Nestle SA", "100000", isin=NESTLE)]
    facts += [fee(10 + i, code, str(v)) for i, (code, v) in enumerate(lines)]
    r = run([STATEMENT, report(ps=start.isoformat(), pe=end.isoformat())], facts)
    assert_invariants(r)
    total = Decimal(r["current"]["total_known"])
    # never more than the lines annualised from a 28-day floor; never negative
    positive = sum((v for _c, v in lines if v > 0), Decimal(0))
    assert Decimal(0) <= total <= positive * 365 / 28 + Decimal("0.01")
