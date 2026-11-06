"""Fee atoms and the inclusion-aware aggregation that produces cost views.

Hard rules enforced here (each has a test):
* UNKNOWN is never summed as zero. It is listed separately and makes the view incomplete.
* A child atom ``included_in`` a parent (e.g. AMF inside OCF, custody inside an all-in fee)
  is shown as detail but never added on top of its parent.
* An atom that ``corroborates`` another (e.g. the cash debit matching the annual fee report)
  is evidence for the same economic cost and is not added twice. Amount mismatches are flagged.
* ILLUSTRATIVE (KID example) and MAXIMUM (KID entry/exit maxima) amounts are never treated
  as costs actually paid.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from .money import ZERO, D, bps_of


class Measurement(StrEnum):
    OBSERVED = "observed"  # charged and documented (statement, debit advice, ex-post report)
    CONTRACTUAL = "contractual"  # derived from the client's own agreement/tariff, not seen debited
    PUBLIC_TARIFF = "public_tariff"  # bank's public list price; weak evidence of what this client pays
    ESTIMATED = "estimated"  # modelled from a dated disclosure (e.g. KID OCF × holding value)
    ILLUSTRATIVE = "illustrative"  # manufacturer hypothetical example; never a paid cost
    MAXIMUM = "maximum"  # disclosed upper bound (e.g. entry charge up to 3%); not actual
    UNKNOWN = "unknown"  # cost category applies but no evidence; NEVER zero
    NOT_APPLICABLE = "not_applicable"  # category does not apply (e.g. no Lombard loan)


class Incidence(StrEnum):
    BILLED = "billed"  # cash debit on the client account
    EMBEDDED = "embedded"  # borne inside NAV / product price
    TAX = "tax"  # transaction taxes / VAT
    CREDIT = "credit"  # rebate actually credited to the client (negative)


class Layer(StrEnum):
    """Layers L1-L10 of data/taxonomy/fee_taxonomy.csv."""

    SERVICE = "L1"  # management, advisory, all-in, external asset manager
    CUSTODY = "L2"  # custody and account
    TRADING = "L3"  # explicit transaction costs: brokerage, FX commission
    PRODUCT = "L4"  # funds and ETFs, embedded in NAV
    STRUCTURED = "L5"  # structured products, embedded in price
    IMPLICIT = "L6"  # FX margin, bid/ask
    WRAPPER = "L7"  # insurance wrapper
    FINANCING = "L8"
    TAX = "L9"  # VAT, stamp duty
    ONE_OFF = "L10"  # switching and one-off
    OTHER = "other"


COUNTABLE = {Measurement.OBSERVED, Measurement.CONTRACTUAL, Measurement.PUBLIC_TARIFF, Measurement.ESTIMATED}


@dataclass
class FeeAtom:
    atom_id: str
    fee_code: str
    layer: Layer
    label: str
    institution: str | None
    amount: Decimal | None  # annualized, reporting currency
    measurement: Measurement
    incidence: Incidence
    account_id: str | None = None
    instrument_id: str | None = None
    recurring: bool = True
    included_in: str | None = None
    corroborates: str | None = None
    rate_bps: Decimal | None = None
    basis_amount: Decimal | None = None
    evidence_ids: tuple[str, ...] = ()
    formula: str = ""
    note: str = ""
    materiality: str = "material"  # material | minor

    def __post_init__(self) -> None:
        if self.amount is not None:
            self.amount = D(self.amount)
        if self.measurement == Measurement.UNKNOWN and self.amount is not None:
            raise ValueError(f"{self.atom_id}: UNKNOWN atom must not carry an amount")
        if self.measurement in COUNTABLE and self.amount is None:
            raise ValueError(f"{self.atom_id}: {self.measurement} atom needs an amount (use UNKNOWN instead)")
        if self.measurement == Measurement.OBSERVED and not self.evidence_ids:
            raise ValueError(f"{self.atom_id}: an observed cost must cite evidence")


class AtomRole(StrEnum):
    COUNTED = "counted"
    INCLUDED_IN_PARENT = "included_in_parent"
    CORROBORATING = "corroborating"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    NOT_A_PAID_COST = "not_a_paid_cost"  # illustrative / maximum
    ONE_OFF = "one_off"


@dataclass
class LedgerSummary:
    total_known: Decimal
    billed_known: Decimal
    embedded_known: Decimal
    by_measurement: dict[str, Decimal]
    by_layer: dict[str, Decimal]
    by_institution: dict[str, Decimal]
    by_instrument: dict[str, Decimal]
    roles: dict[str, AtomRole]
    unknown: list[FeeAtom]
    one_off_known: Decimal
    warnings: list[str] = field(default_factory=list)
    scope_aum: Decimal | None = None

    @property
    def is_complete(self) -> bool:
        return not any(a.materiality == "material" for a in self.unknown)

    @property
    def total_bps(self) -> Decimal | None:
        return bps_of(self.total_known, self.scope_aum) if self.scope_aum else None

    @property
    def verified_share(self) -> Decimal | None:
        """Share of the known total backed by observed charges (0..1)."""
        if self.total_known == 0:
            return None
        return self.by_measurement.get(Measurement.OBSERVED.value, ZERO) / self.total_known


def _check_graph(atoms: dict[str, FeeAtom]) -> None:
    for a in atoms.values():
        for ref, kind in ((a.included_in, "included_in"), (a.corroborates, "corroborates")):
            if ref is not None and ref not in atoms:
                raise ValueError(f"{a.atom_id}: {kind} references missing atom {ref}")
        if a.included_in and a.corroborates:
            raise ValueError(f"{a.atom_id}: an atom cannot be both a sub-component and a duplicate")
    # cycle detection on included_in / corroborates edges
    for start in atoms:
        seen, cur = set(), start
        while cur is not None:
            if cur in seen:
                raise ValueError(f"cycle in fee inclusion graph at {cur}")
            seen.add(cur)
            nxt = atoms[cur]
            cur = nxt.included_in or nxt.corroborates


def aggregate(atoms: list[FeeAtom], scope_aum: object | None = None, tolerance: object = "0.05") -> LedgerSummary:
    by_id: dict[str, FeeAtom] = {}
    for a in atoms:
        if a.atom_id in by_id:
            raise ValueError(f"duplicate atom id {a.atom_id}")
        by_id[a.atom_id] = a
    _check_graph(by_id)

    roles: dict[str, AtomRole] = {}
    warnings: list[str] = []
    for a in atoms:
        if a.measurement == Measurement.NOT_APPLICABLE:
            roles[a.atom_id] = AtomRole.NOT_APPLICABLE
        elif a.measurement == Measurement.UNKNOWN:
            roles[a.atom_id] = AtomRole.UNKNOWN
        elif a.measurement in (Measurement.ILLUSTRATIVE, Measurement.MAXIMUM):
            roles[a.atom_id] = AtomRole.NOT_A_PAID_COST
        elif a.included_in:
            roles[a.atom_id] = AtomRole.INCLUDED_IN_PARENT
        elif a.corroborates:
            roles[a.atom_id] = AtomRole.CORROBORATING
            target = by_id[a.corroborates]
            if target.amount is not None and a.amount is not None:
                diff = abs(target.amount - a.amount)
                base = max(abs(target.amount), Decimal("1"))
                if diff / base > D(tolerance):
                    warnings.append(
                        f"{a.label}: {a.amount:,.2f} does not match {target.label} {target.amount:,.2f} "
                        f"(difference {diff:,.2f}); review which source is correct."
                    )
        elif not a.recurring:
            roles[a.atom_id] = AtomRole.ONE_OFF
        else:
            roles[a.atom_id] = AtomRole.COUNTED

    # children whose parent is unknown cannot inherit a count either: parent drives the total
    for a in atoms:
        if roles[a.atom_id] == AtomRole.INCLUDED_IN_PARENT and roles[a.included_in] == AtomRole.UNKNOWN:
            warnings.append(f"{a.label} is a sub-component of an unknown parent; parent total still required.")
        if roles[a.atom_id] == AtomRole.INCLUDED_IN_PARENT:
            parent = by_id[a.included_in]
            if parent.amount is not None and a.amount is not None and a.amount > parent.amount:
                warnings.append(f"{a.label} exceeds its inclusive parent {parent.label}; check the disclosure.")

    total = billed = embedded = one_off = ZERO
    by_meas: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_layer: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_inst: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_instr: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for a in atoms:
        role = roles[a.atom_id]
        if role == AtomRole.ONE_OFF:
            one_off += a.amount or ZERO
            continue
        if role != AtomRole.COUNTED:
            continue
        amt = a.amount
        assert amt is not None
        total += amt
        if a.incidence == Incidence.EMBEDDED:
            embedded += amt
        else:
            billed += amt
        by_meas[a.measurement.value] += amt
        by_layer[a.layer.value] += amt
        by_inst[a.institution or "Unassigned"] += amt
        if a.instrument_id:
            by_instr[a.instrument_id] += amt

    unknown = [a for a in atoms if roles[a.atom_id] == AtomRole.UNKNOWN]
    return LedgerSummary(
        total_known=total,
        billed_known=billed,
        embedded_known=embedded,
        by_measurement=dict(by_meas),
        by_layer=dict(by_layer),
        by_institution=dict(by_inst),
        by_instrument=dict(by_instr),
        roles=roles,
        unknown=unknown,
        one_off_known=one_off,
        warnings=warnings,
        scope_aum=D(scope_aum) if scope_aum is not None else None,
    )
