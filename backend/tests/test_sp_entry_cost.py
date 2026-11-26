"""SC-7.17: a structured product's entry cost is paid once, so it is a one-off, not a yearly cost.

Before the fix product_atoms left SP_ENTRY_COST recurring, and a 2% issuer margin was added to the
annual total every year.
"""

from __future__ import annotations

from decimal import Decimal

from pce.finance.ledger import aggregate
from pce.finance.scenarios import HoldingInput, ProductRate, product_atoms

ISIN = "CH0000000001"  # SYNTHETIC


def test_sp_entry_cost_is_one_off_and_running_cost_is_annual() -> None:
    h = HoldingInput(
        ISIN, "Synthetic Barrier Reverse Convertible", "STRUCTURED", Decimal("100000"), "Bank", "Bank"
    )
    rates = [
        ProductRate(ISIN, "SP_ENTRY_COST", Decimal("2.0")),
        ProductRate(ISIN, "SP_ONGOING", Decimal("0.5")),
    ]
    s = aggregate(product_atoms([h], rates, "cur"))
    assert s.total_known == Decimal("500")
    assert s.one_off_known == Decimal("2000")
