"""Hidden costs the portfolio implies but the documents do not quantify (COST_PROTOCOL.md step 6).

These rows are never ledger atoms: Ale decided (2026-11-25) that implicit costs are shown as a separate
range and never added to the headline totals. Until SC-7.14 can estimate them from trade data and
reference rates, each row says the cost is not estimated and which document would let us estimate it.
A row is listed, not invented: no amount, no typical band without a recorded source.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from .money import ZERO


@dataclass(frozen=True)
class HiddenCost:
    key: str
    fee_code: str
    label: str
    institution: str
    basis: Decimal | None  # base-currency value of the holdings the cost applies to; None if unvalued
    needs: str
    note: str = ""
    status: str = "not_estimated"


def hidden_costs(holdings: list[dict], base_ccy: str, observed: set[tuple[str, str]]) -> list[HiddenCost]:
    """Expected implicit costs per institution.

    holdings: analysis holdings ({institution, asset_class, currency, value}); observed: (institution,
    fee_code) pairs already evidenced, which are not listed again.
    """
    by_inst: dict[str, list[dict]] = defaultdict(list)
    for h in holdings:
        by_inst[h["institution"]].append(h)

    def basis(rows: list[dict]) -> Decimal | None:
        vals = [h["value"] for h in rows if h["value"] is not None]
        return sum(vals, ZERO) if vals else None

    out: list[HiddenCost] = []
    for ik in sorted(by_inst):
        rows = by_inst[ik]
        foreign = [h for h in rows if (h["currency"] or base_ccy) != base_ccy]
        invested = [h for h in rows if h["asset_class"] != "CASH"]
        if foreign and (ik, "FX_MARGIN") not in observed:
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
        if invested and (ik, "STAMP_DUTY_CH") not in observed:
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
