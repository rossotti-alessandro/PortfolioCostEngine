"""Contractual fee rules: bps, tiers (marginal or whole-base), min/max, proration.

A tariff is only applicable to an account booked in the same jurisdiction as the
legal entity that issued it. Applying, e.g., a Luxembourg price schedule to a
Swiss-booked account is rejected, never silently accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from decimal import Decimal

from .money import BPS, ZERO, D


class TierMethod(StrEnum):
    MARGINAL = "marginal"  # each band's rate applies to the slice in that band
    WHOLE_BASE = "whole_base"  # the band reached applies to the whole base


def bps_fee(base: object, bps: object, minimum: object = 0, maximum: object | None = None):
    base_d, bps_d, min_d = D(base), D(bps), D(minimum)
    if base_d < 0:
        raise ValueError("negative fee base")
    if maximum is not None and min_d > D(maximum):
        raise ValueError("minimum exceeds maximum: check the contract data entry")
    amount = base_d * bps_d / BPS
    amount = max(amount, min_d)
    if maximum is not None:
        amount = min(amount, D(maximum))
    return amount


def _validate_tiers(tiers: list[tuple[object | None, object]]) -> list[tuple[Decimal | None, Decimal]]:
    if not tiers:
        raise ValueError("empty tier schedule")
    out = []
    prev = ZERO
    for i, (upper, rate) in enumerate(tiers):
        if upper is None:
            if i != len(tiers) - 1:
                raise ValueError("open-ended tier must be last")
        else:
            u = D(upper)
            if u <= prev:
                raise ValueError("tier bounds must be strictly ascending")
            prev = u
        out.append((None if upper is None else D(upper), D(rate)))
    return out


def marginal_tier_fee(base: object, tiers: list[tuple[object | None, object]]):
    base_d = D(base)
    if base_d < 0:
        raise ValueError("negative fee base")
    t = _validate_tiers(tiers)
    total, lower = ZERO, ZERO
    for upper, rate in t:
        top = base_d if upper is None else min(base_d, upper)
        if top > lower:
            total += (top - lower) * rate / BPS
        if upper is None or base_d <= upper:
            return total
        lower = upper
    raise ValueError("tier schedule does not cover the base")


def whole_base_tier_fee(base: object, tiers: list[tuple[object | None, object]]):
    base_d = D(base)
    if base_d < 0:
        raise ValueError("negative fee base")
    for upper, rate in _validate_tiers(tiers):
        if upper is None or base_d <= upper:
            return base_d * rate / BPS
    raise ValueError("tier schedule does not cover the base")


def prorate(annual: object, days: int, day_count: int = 365):
    if not 0 <= days <= 366:
        raise ValueError("invalid period length")
    if day_count not in (360, 365, 366):
        raise ValueError("unsupported day count")
    return D(annual) * D(days) / D(day_count)


def annualize(amount: object, days: int, day_count: int = 365):
    if days <= 0:
        raise ValueError("period must be positive to annualize")
    return D(amount) * D(day_count) / D(days)


@dataclass(frozen=True)
class FeeRule:
    """One component of a price schedule, evaluated on an annual basis."""

    fee_code: str
    label: str
    base: str  # "aum" | "custody_eligible" | "trade_notional" | "fx_notional" | "fees" | "fixed"
    rate_bps: object | None = None
    tiers: list[tuple[object | None, object]] | None = None
    tier_method: TierMethod = TierMethod.MARGINAL
    flat_amount: object | None = None
    minimum: object = 0
    maximum: object | None = None
    included_fee_codes: tuple[str, ...] = ()  # all-in fee covers these codes

    def annual_amount(self, base_amount: object):
        if self.base == "fixed":
            if self.flat_amount is None:
                raise ValueError(f"{self.fee_code}: fixed fee without amount")
            return D(self.flat_amount)
        if self.tiers:
            fn = marginal_tier_fee if self.tier_method == TierMethod.MARGINAL else whole_base_tier_fee
            amount = fn(base_amount, self.tiers)
            amount = max(amount, D(self.minimum))
            if self.maximum is not None:
                amount = min(amount, D(self.maximum))
            return amount
        if self.rate_bps is None:
            raise ValueError(f"{self.fee_code}: rule has neither rate nor tiers")
        return bps_fee(base_amount, self.rate_bps, self.minimum, self.maximum)

    def formula(self, base_amount: object) -> str:
        b = f"{D(base_amount):,.2f}"
        if self.base == "fixed":
            return f"fixed {D(self.flat_amount):,.2f}"
        if self.tiers:
            bands = "; ".join(
                f"{'≤' + format(D(u), ',.0f') if u is not None else 'above'} @ {D(r)} bps" for u, r in self.tiers
            )
            return f"{self.tier_method.value} tiers on {b} [{bands}]" + (f", min {D(self.minimum):,.2f}" if D(self.minimum) else "")
        s = f"{b} × {D(self.rate_bps)} bps / 10'000"
        if D(self.minimum):
            s += f", min {D(self.minimum):,.2f}"
        if self.maximum is not None:
            s += f", max {D(self.maximum):,.2f}"
        return s


@dataclass(frozen=True)
class Tariff:
    tariff_id: str
    issuer: str
    legal_entity_jurisdiction: str  # ISO country of the booking entity, e.g. "CH", "LU"
    effective_from: date
    effective_to: date | None
    currency: str
    rules: tuple[FeeRule, ...] = field(default_factory=tuple)

    def applicability(self, booking_jurisdiction: str, on: date) -> tuple[bool, str | None]:
        if self.legal_entity_jurisdiction.upper() != booking_jurisdiction.upper():
            return False, (
                f"Tariff issued by a {self.legal_entity_jurisdiction} entity cannot be applied to an account "
                f"booked in {booking_jurisdiction}."
            )
        if on < self.effective_from or (self.effective_to and on > self.effective_to):
            return False, f"Tariff not in force on {on.isoformat()} (stale or future source)."
        return True, None
