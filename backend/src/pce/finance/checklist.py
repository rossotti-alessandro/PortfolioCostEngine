"""Hidden costs the portfolio implies but the documents do not quantify (COST_PROTOCOL.md step 6).

These rows are never ledger atoms: Ale decided (2026-11-25) that implicit costs are shown as a separate
range and never added to the headline totals. A row with the data for an estimate carries a range (cash
drag, SC-7.14: from 0 to the benchmark rate x cash); the others say the cost is not estimated and which
document would let us estimate it. A row is listed, not invented: no typical band without a recorded source.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .implicit import cash_drag_range, fx_margin, stamp_duty
from .money import ZERO, D


@dataclass(frozen=True)
class HiddenCost:
    key: str
    fee_code: str
    label: str
    institution: str
    basis: Decimal | None  # base-currency value of the holdings the cost applies to; None if unvalued
    needs: str
    note: str = ""
    status: str = "not_estimated"  # or "range": low..high is the estimate, never added to a total
    low: Decimal | None = None
    high: Decimal | None = None
    method: str = ""


def hidden_costs(
    holdings: list[dict],
    base_ccy: str,
    observed: set[tuple[str, str]],
    cash_rates: dict[str, dict] | None = None,
    trades: list[dict] | None = None,
    trade_years: dict[str, Decimal | None] | None = None,
    ref_fx: dict[str, dict[str, dict]] | None = None,
) -> list[HiddenCost]:
    """Expected implicit costs per institution.

    holdings: analysis holdings ({institution, asset_class, currency, value}); observed: (institution,
    fee_code) pairs already evidenced, which are not listed again; cash_rates: 12-month benchmark averages
    per currency from ``implicit.benchmark_rates``; trades: analysis transactions (SC-7.18); trade_years:
    years each bank's transaction lists cover, None when too short or unknown to annualise; ref_fx: ECB
    reference rates by date (SC-7.11).
    """
    by_inst: dict[str, list[dict]] = defaultdict(list)
    for h in holdings:
        by_inst[h["institution"]].append(h)

    def basis(rows: list[dict]) -> Decimal | None:
        vals = [h["value"] for h in rows if h["value"] is not None]
        return sum(vals, ZERO) if vals else None

    by_trades: dict[str, list[dict]] = defaultdict(list)
    for t in trades or []:
        by_trades[t["institution"]].append(t)

    def measured(
        ik: str,
        label: str,
        code: str,
        costs: list[Decimal | None],
        what: str,
        how: str,
        note: str,
        needs: str,
        base_value: Decimal | None,
    ) -> HiddenCost | None:
        """A row estimated from the trades, annualised over the period the lists cover (SC-7.23)."""
        known = [c for c in costs if c is not None]
        if not known:
            return None
        total, years = sum(known, ZERO), (trade_years or {}).get(ik)
        amount = (total / years if years else total).quantize(Decimal("0.01"))
        span = (
            "a year" if years else "over the listed trades only (period too short or unknown: a lower bound)"
        )
        skipped = len(costs) - len(known)
        return HiddenCost(
            f"hidden:{ik}:{code}", code, label, ik, base_value, needs,
            note + (f" {skipped} {what} without data for an estimate are not counted." if skipped else ""),
            "range", amount, amount, f"{len(known)} {what}: {how}, {span}",
        )  # fmt: skip

    out: list[HiddenCost] = []
    for ik in sorted(set(by_inst) | set(by_trades)):
        rows = by_inst[ik]
        ik_trades = by_trades[ik]
        foreign = [h for h in rows if (h["currency"] or base_ccy) != base_ccy]
        invested = [h for h in rows if h["asset_class"] != "CASH"]
        cash_by_ccy: dict[str, list[dict]] = defaultdict(list)
        for h in rows:
            if h["asset_class"] == "CASH":
                cash_by_ccy[h["currency"] or base_ccy].append(h)
        for ccy in sorted(cash_by_ccy):
            cash = basis(cash_by_ccy[ccy])
            ref = (cash_rates or {}).get(ccy)
            label = f"Cash drag on {ccy} cash"
            needs = "Cash account statements showing the interest credited"
            if cash is None or ref is None:
                out.append(
                    HiddenCost(
                        f"hidden:{ik}:CASH_DRAG:{ccy}",
                        "CASH_DRAG",
                        label,
                        ik,
                        cash,
                        needs,
                        "Cash earns less than the market rate when the bank credits little or no interest.",
                    )
                )
                continue
            low, high = cash_drag_range(cash, D(ref["rate_pct"]))
            first, last, n = ref["months"]
            out.append(
                HiddenCost(
                    f"hidden:{ik}:CASH_DRAG:{ccy}",
                    "CASH_DRAG",
                    label,
                    ik,
                    cash,
                    needs,
                    f"From 0 if {ik} pays the market rate to the full {ref['benchmark']} if it pays nothing. "
                    "Cash at the statement date stands in for the average cash of the year.",
                    "range",
                    low,
                    high.quantize(Decimal("0.01")),
                    f"{cash:,.2f} × 0 … {ref['benchmark']} {ref['rate_pct']}% "
                    f"(average of {n} months {first} to {last}; {ref['source']})",
                )
            )
        fx_trades = [t for t in ik_trades if t["side"] == "fx"]
        fx_row = measured(
            ik, "FX margin on currency exchanges", "FX_MARGIN",
            [fx_margin(t, base_ccy, ref_fx or {}) for t in fx_trades], "conversions",
            "|rate applied − ECB reference rate that day| × amount",
            "The ECB fixes once a day: the gap also holds the market move between the fixing and the trade.",
            "FX confirmations, or a transaction list showing the rate applied", basis(foreign),
        )  # fmt: skip
        if fx_row and (ik, "FX_MARGIN") not in observed:
            out.append(fx_row)
        elif (foreign or fx_trades) and (ik, "FX_MARGIN") not in observed:
            out.append(
                HiddenCost(
                    f"hidden:{ik}:FX_MARGIN",
                    "FX_MARGIN",
                    "FX margin on currency exchanges",
                    ik,
                    basis(foreign),
                    "FX confirmations, or a transaction list showing the rate applied",
                    f"Holdings outside {base_ccy}: any purchase, sale or income conversion pays a margin "
                    "over the reference rate.",
                )
            )
        if invested and (ik, "BID_ASK_SPREAD") not in observed:
            out.append(
                HiddenCost(
                    f"hidden:{ik}:BID_ASK_SPREAD",
                    "BID_ASK_SPREAD",
                    "Spreads and dealer mark-ups on trades",
                    ik,
                    basis(invested),
                    "Transaction list for the period",
                    "Only if the portfolio traded during the year. Market cost, not bank revenue.",
                )
            )
        stamp_row = measured(
            ik, "Swiss stamp duty on trades", "STAMP_DUTY_CH",
            [stamp_duty(t, base_ccy, ref_fx or {}) for t in ik_trades if t["side"] in ("buy", "sell")],
            "trades", "trade value × 0.075% (Swiss securities) or 0.15% (foreign), the client's half of the "
            "transfer tax (StG art. 16)",
            "Exempt trades (money-market paper, new issues) would lower it.",
            "Transaction list or trade confirmations", basis(invested),
        )  # fmt: skip
        if stamp_row and (ik, "STAMP_DUTY_CH") not in observed:
            out.append(stamp_row)
        elif (invested or ik_trades) and (ik, "STAMP_DUTY_CH") not in observed:
            out.append(
                HiddenCost(
                    f"hidden:{ik}:STAMP_DUTY_CH",
                    "STAMP_DUTY_CH",
                    "Transaction taxes (stamp duty, FTT)",
                    ik,
                    basis(invested),
                    "Transaction list or trade confirmations",
                    "A tax: any bank charges it, so it does not change a same-holdings saving.",
                )
            )
    return out
