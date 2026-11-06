"""Scenario comparison: current vs proposal, first-year net, payback, internal margin.

The saving statement is bounded by data completeness:
* current incomplete, proposal complete  -> saving is a LOWER bound ("at least")
* current complete,  proposal incomplete -> saving is an UPPER bound ("at most")
* both incomplete                         -> INDETERMINATE (known difference shown with caveat)
* both complete                           -> POINT estimate
A proposal that changes instruments is never presented as a pure fee saving.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from .ledger import FeeAtom, Incidence, Layer, LedgerSummary, Measurement
from .money import ZERO, D, bps_of, money
from .tariff import FeeRule

LAYER_BY_CODE = {
    "MGMT_DISCRETIONARY": Layer.SERVICE,
    "ADVISORY_FEE": Layer.SERVICE,
    "ALL_IN_FEE": Layer.SERVICE,
    "EAM_FEE": Layer.SERVICE,
    "PLATFORM_FIXED": Layer.SERVICE,
    "CUSTODY_FEE": Layer.CUSTODY,
    "ACCOUNT_FEE": Layer.CUSTODY,
    "BROKERAGE": Layer.TRADING,
    "TICKET_FEE": Layer.TRADING,
    "FX_COMMISSION": Layer.TRADING,
    "VAT_ON_FEES": Layer.TAX,
    "STAMP_DUTY_CH": Layer.TAX,
}


class Bound(StrEnum):
    POINT = "point"
    LOWER = "at_least"
    UPPER = "at_most"
    INDETERMINATE = "indeterminate"


@dataclass
class Comparison:
    current_known: Decimal
    proposal_known: Decimal
    annual_saving: Decimal
    annual_saving_bps: Decimal | None
    bound: Bound
    migration_one_off: Decimal
    first_year_net: Decimal
    payback_months: Decimal | None
    like_for_like: bool
    caveats: list[str] = field(default_factory=list)


def compare(
    current: LedgerSummary,
    proposal: LedgerSummary,
    migration_one_off: object = 0,
    like_for_like: bool = True,
    current_complete: bool | None = None,
    proposal_complete: bool | None = None,
) -> Comparison:
    """``*_complete`` overrides let the caller ignore unknowns that are identical on both
    sides (same instrument, same fee code held unchanged): they cancel in the difference."""
    mig = D(migration_one_off)
    if mig < 0:
        raise ValueError("migration cost cannot be negative")
    saving = current.total_known - proposal.total_known
    cur_ok = current.is_complete if current_complete is None else current_complete
    prop_ok = proposal.is_complete if proposal_complete is None else proposal_complete
    if cur_ok and prop_ok:
        bound = Bound.POINT
    elif not cur_ok and prop_ok:
        bound = Bound.LOWER
    elif cur_ok and not prop_ok:
        bound = Bound.UPPER
    else:
        bound = Bound.INDETERMINATE
    caveats = []
    if bound == Bound.LOWER:
        caveats.append("Some current costs are unknown; the true saving is likely higher than shown.")
    if bound == Bound.UPPER:
        caveats.append("Some proposal costs are unknown; the true saving may be lower than shown.")
    if bound == Bound.INDETERMINATE:
        caveats.append("Both sides have unknown costs; the difference shown covers known costs only.")
    if not like_for_like:
        caveats.append(
            "Proposal changes instruments. The difference mixes fee effects with changes in product, risk "
            "and possibly tax; it is not a like-for-like fee saving."
        )
    payback = None
    if saving > 0 and mig > 0:
        payback = (mig / saving * 12).quantize(Decimal("0.1"))
    elif saving > 0:
        payback = ZERO
    if saving <= 0:
        caveats.append("No annual saving on known costs: the proposal is not cheaper on this evidence.")
    base = current.scope_aum
    return Comparison(
        current_known=money(current.total_known),
        proposal_known=money(proposal.total_known),
        annual_saving=money(saving),
        annual_saving_bps=bps_of(saving, base) if base else None,
        bound=bound,
        migration_one_off=money(mig),
        first_year_net=money(saving - mig),
        payback_months=payback,
        like_for_like=like_for_like,
        caveats=caveats,
    )


@dataclass(frozen=True)
class HoldingInput:
    instrument_id: str  # ISIN when available, else internal id (cash, derivatives)
    name: str
    asset_class: str
    value: Decimal
    institution: str
    account_id: str


@dataclass(frozen=True)
class ProductRate:
    """A dated product cost rate (percent per year) for an exact share class."""

    instrument_id: str
    fee_code: str  # FUND_ONGOING, FUND_MGMT_FEE, FUND_TRANSACTION, SP_ENTRY_COST, SP_ONGOING …
    rate_pct: Decimal | None  # None means the cost exists but is not disclosed
    included_in_code: str | None = None
    evidence_ids: tuple[str, ...] = ()
    source_label: str = ""


def product_atoms(holdings: list[HoldingInput], rates: list[ProductRate], prefix: str) -> list[FeeAtom]:
    """Turn dated product disclosures into annual economic cost atoms."""
    by_instr: dict[str, list[ProductRate]] = {}
    for r in rates:
        by_instr.setdefault(r.instrument_id, []).append(r)
    atoms: list[FeeAtom] = []
    for h in holdings:
        for r in by_instr.get(h.instrument_id, []):
            aid = f"{prefix}:{h.account_id}:{h.instrument_id}:{r.fee_code}"
            parent = (
                f"{prefix}:{h.account_id}:{h.instrument_id}:{r.included_in_code}"
                if r.included_in_code
                else None
            )
            layer = Layer.STRUCTURED if r.fee_code.startswith("SP_") else Layer.PRODUCT
            if r.rate_pct is None:
                atoms.append(
                    FeeAtom(
                        aid,
                        r.fee_code,
                        layer,
                        h.name,
                        h.institution,
                        None,
                        Measurement.UNKNOWN,
                        Incidence.EMBEDDED,
                        h.account_id,
                        h.instrument_id,
                        evidence_ids=r.evidence_ids,
                        note=r.source_label,
                    )
                )
                continue
            amount = h.value * D(r.rate_pct) / Decimal(100)
            atoms.append(
                FeeAtom(
                    aid,
                    r.fee_code,
                    layer,
                    h.name,
                    h.institution,
                    amount,
                    Measurement.ESTIMATED,
                    Incidence.EMBEDDED,
                    h.account_id,
                    h.instrument_id,
                    included_in=parent,
                    rate_bps=D(r.rate_pct) * 100,
                    basis_amount=h.value,
                    evidence_ids=r.evidence_ids,
                    formula=f"{h.value:,.2f} × {D(r.rate_pct)}% (current value × disclosed annual rate)",
                    note=r.source_label,
                )
            )
    return atoms


def proposal_service_atoms(
    rules: list[FeeRule], bases: dict[str, Decimal], institution: str, prefix: str = "proposal"
) -> list[FeeAtom]:
    atoms = []
    for rule in rules:
        base = bases.get(rule.base, ZERO) if rule.base != "fixed" else ZERO
        amount = rule.annual_amount(base)
        layer = LAYER_BY_CODE.get(rule.fee_code, Layer.OTHER)
        atoms.append(
            FeeAtom(
                f"{prefix}:{rule.fee_code}",
                rule.fee_code,
                layer,
                rule.label,
                institution,
                amount,
                Measurement.CONTRACTUAL,
                Incidence.BILLED,
                formula=rule.formula(base),
                basis_amount=base if rule.base != "fixed" else None,
                rate_bps=D(rule.rate_bps) if rule.rate_bps is not None else None,
            )
        )
    return atoms


@dataclass
class InternalEconomics:
    annual_revenue: Decimal
    annual_servicing_cost: Decimal
    onboarding_one_off: Decimal
    annual_contribution: Decimal
    first_year_contribution: Decimal
    margin_pct: Decimal | None
    verdict: str
    reasons: list[str]


def internal_economics(
    revenue_atoms: list[FeeAtom],
    annual_servicing_cost: object,
    onboarding_one_off: object,
    comparison: Comparison,
    evidence_complete: bool,
    min_margin_pct: object = "25",
) -> InternalEconomics:
    """Firm-side contribution margin. INTERNAL ONLY: never included in a client report."""
    revenue = sum((a.amount or ZERO for a in revenue_atoms), ZERO)
    cost = D(annual_servicing_cost)
    onboard = D(onboarding_one_off)
    contribution = revenue - cost
    margin = (contribution / revenue * 100).quantize(Decimal("0.1")) if revenue else None
    reasons = []
    if not evidence_complete:
        verdict = "insufficient_evidence"
        reasons.append("Material current costs are unknown: request the missing documents before deciding.")
    elif comparison.annual_saving <= 0:
        verdict = "no_client_benefit"
        reasons.append("The client would not save on known costs.")
    elif margin is None or margin < D(min_margin_pct):
        verdict = "below_margin_threshold"
        reasons.append(f"Contribution margin below the {D(min_margin_pct)}% threshold set by management.")
    else:
        verdict = "proceed_to_senior_review"
        reasons.append(
            "Client saves and the firm earns a margin above threshold; senior approval still required."
        )
    return InternalEconomics(
        revenue, cost, onboard, contribution, contribution - onboard, margin, verdict, reasons
    )
