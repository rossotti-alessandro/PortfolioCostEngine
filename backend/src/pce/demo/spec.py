"""Single source of truth for the SYNTHETIC demo prospect.

Every institution, person, ISIN and amount here is invented. ISINs use country
code ``ZZ`` (not an ISO 3166 country) so they cannot collide with real securities.
The generator renders these facts into documents; the extraction pipeline must then
recover them from the documents alone. The golden-label tests compare the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as Dec

PROSPECT_CODE = "P-1042"
PROSPECT_LABEL = "Prospect P-1042 (synthetic)"
CLIENT_DOMICILE = (
    "CH"  # decides Swiss VAT on fees (services to clients abroad are generally VAT-exempt; to verify)
)
VALUATION_DATE = "2026-09-30"
PERIOD = ("2025-10-01", "2026-09-30")
USD_CHF = Dec("0.8000")  # rate printed on the Bank Beta statement (synthetic)

ALPHA = "Bank Alpha (Synthetic) SA"
ALPHA_CITY = "Lugano, Switzerland"
BETA = "Bank Beta (Synthetic) AG"
BETA_CITY = "Zurich, Switzerland"
BETA_LU = "Bank Beta (Synthetic) Europe S.A."
BETA_LU_CITY = "Luxembourg"


@dataclass(frozen=True)
class Pos:
    isin: str | None
    name: str
    asset_class: str
    quantity: Dec | None
    price: Dec | None
    ccy: str
    value_ccy: Dec
    value_chf: Dec


ALPHA_POSITIONS = [
    Pos(
        "ZZGEQLDRA013",
        "Global Equity Leaders Fund A CHF",
        "FUND",
        Dec("4500"),
        Dec("200.00"),
        "CHF",
        Dec("900000.00"),
        Dec("900000.00"),
    ),
    Pos(
        "ZZWLDIDX0014",
        "World Index ETF CHF Hedged",
        "ETF",
        Dec("15000"),
        Dec("50.00"),
        "CHF",
        Dec("750000.00"),
        Dec("750000.00"),
    ),
    Pos(
        "ZZCHFBND0R18",
        "Swiss Franc Bond Fund R",
        "FUND",
        Dec("5000"),
        Dec("120.00"),
        "CHF",
        Dec("600000.00"),
        Dec("600000.00"),
    ),
    Pos(
        "ZZSYNIND0015",
        "Synthetic Industries AG reg.",
        "EQUITY",
        Dec("3000"),
        Dec("150.00"),
        "CHF",
        Dec("450000.00"),
        Dec("450000.00"),
    ),
    Pos(
        "ZZBRCSMI0010",
        "Barrier Reverse Convertible on SMI 2027",
        "STRUCTURED",
        Dec("300"),
        Dec("1000.00"),
        "CHF",
        Dec("300000.00"),
        Dec("300000.00"),
    ),
    Pos(None, "Current account CHF", "CASH", None, None, "CHF", Dec("200000.00"), Dec("200000.00")),
]
ALPHA_TOTAL = Dec("3200000.00")

BETA_POSITIONS = [
    Pos(
        "ZZUSGRI00019",
        "US Growth Equity Fund I USD",
        "FUND",
        Dec("2000"),
        Dec("250.00"),
        "USD",
        Dec("500000.00"),
        Dec("400000.00"),
    ),
    Pos(
        "ZZEMMKTA0019",
        "Emerging Markets Opportunities Fund A",
        "FUND",
        Dec("3500"),
        Dec("100.00"),
        "CHF",
        Dec("350000.00"),
        Dec("350000.00"),
    ),
    Pos(
        "ZZSYNPHA0017",
        "Synthetic Pharma AG",
        "EQUITY",
        Dec("1000"),
        Dec("250.00"),
        "CHF",
        Dec("250000.00"),
        Dec("250000.00"),
    ),
    Pos(None, "Cash account CHF", "CASH", None, None, "CHF", Dec("100000.00"), Dec("100000.00")),
]
BETA_TOTAL = Dec("1100000.00")

# Bank Alpha ex-post annual costs and charges report (observed, CHF)
ALPHA_COST_REPORT = [
    ("Advisory mandate fee", "ADVISORY_FEE", Dec("25600.00")),
    ("Custody fee", "CUSTODY_FEE", Dec("6000.00")),
    ("Brokerage commissions", "BROKERAGE", Dec("4150.00")),
    ("Foreign exchange commissions", "FX_COMMISSION", Dec("1240.00")),
    ("Swiss stamp duty", "STAMP_DUTY_CH", Dec("610.00")),
    ("VAT on fees", "VAT_ON_FEES", Dec("2559.60")),  # 8.1% on advisory 25,600 + custody 6,000
]
ALPHA_REPORTED_PRODUCT_COSTS = Dec("17640.00")  # bank's own ex-post estimate of third-party product costs
ALPHA_RETROCESSIONS = Dec("3900.00")  # disclosed retrocessions retained by the bank (information)

# Bank Alpha quarterly debits on the Italian-language cash statement (Q3 2026)
ALPHA_CASH_DEBITS = [
    ("2026-07-01", "Commissione di consulenza 3° trimestre 2026", "ADVISORY_FEE", Dec("6400.00")),
    ("2026-07-01", "Commissione di custodia 3° trimestre 2026", "CUSTODY_FEE", Dec("1500.00")),
]

# Bank Alpha price schedule (CH entity) — contractual
ALPHA_TARIFF = {
    "advisory_pct": Dec("0.80"),
    "custody_pct": Dec("0.20"),
    "custody_min": Dec("1000.00"),
    "brokerage_pct": Dec("0.50"),
    "brokerage_min": Dec("80.00"),
    "transfer_out_per_position": Dec("100.00"),
}
# Bank Beta Luxembourg schedule — must be rejected for a CH-booked account
BETA_LU_TARIFF = {"custody_pct": Dec("0.30"), "custody_min_quarter": Dec("360.00")}

# Product disclosures (synthetic KIDs). rate in percent per year.
KIDS = {
    "ZZGEQLDRA013": {
        "name": "Global Equity Leaders Fund A CHF",
        "manufacturer": "Synthetic Asset Management S.A.",
        "ongoing": Dec("1.08"),
        "mgmt_included": Dec("0.75"),
        "transaction": Dec("0.18"),
        "entry_max": Dec("3.00"),
        "exit": Dec("0.00"),
        "performance": Dec("0.00"),
        "date": "2026-02-15",
    },
    "ZZWLDIDX0014": {
        "name": "World Index ETF CHF Hedged",
        "manufacturer": "Synthetic Index Partners plc",
        "ongoing": Dec("0.12"),
        "mgmt_included": None,
        "transaction": Dec("0.02"),
        "entry_max": Dec("0.00"),
        "exit": Dec("0.00"),
        "performance": Dec("0.00"),
        "date": "2026-03-01",
    },
    "ZZCHFBND0R18": {
        "name": "Swiss Franc Bond Fund R",
        "manufacturer": "Synthetic Fixed Income AG",
        "ongoing": Dec("0.85"),
        "mgmt_included": Dec("0.60"),
        "transaction": Dec("0.10"),
        "entry_max": Dec("2.00"),
        "exit": Dec("0.00"),
        "performance": Dec("0.00"),
        "date": "2026-01-20",
    },
    "ZZUSGRI00019": {
        "name": "US Growth Equity Fund I USD",
        "manufacturer": "Synthetic Growth Advisors LLC",
        "ongoing": Dec("0.55"),
        "mgmt_included": Dec("0.45"),
        "transaction": Dec("0.25"),
        "entry_max": Dec("0.00"),
        "exit": Dec("0.00"),
        "performance": Dec("0.00"),
        "date": "2026-04-10",
    },
    # ZZEMMKTA0019: intentionally NO KID provided -> product cost UNKNOWN -> request generated
}
STRUCTURED_TERMSHEET = {
    "isin": "ZZBRCSMI0010",
    "name": "Barrier Reverse Convertible on SMI 2027",
    "issuer": "Synthetic Issuer Bank Ltd",
    "distribution_fee_max": Dec("1.00"),  # "up to 1.00% p.a." -> MAXIMUM, not counted
    "issuer_margin": None,  # not disclosed -> UNKNOWN (material)
    "date": "2025-11-14",
}

# Proposal defaults (editable in the UI). Firm name is white-label.
PROPOSAL_DEFAULTS = {
    "firm_name": "Safe Capital (proposal)",
    "custodian": "Partner custodian (CH)",
    "eam_tiers": [["2000000", "70"], [None, "50"]],  # Safe Capital fee as external asset manager (EAM_FEE)
    "eam_tier_method": "marginal",
    "vat_pct": "8.1",  # Swiss VAT on fees, applied only when the client is domiciled in CH
    "custody_bps": "10",
    "custody_min": "1500",
    "brokerage_bps": "10",
    "fx_bps": "10",
    "annual_turnover_chf": "830000",  # derived from Bank Alpha brokerage 4,150 at 0.50%; editable
    "fx_notional_chf": "310000",  # derived from FX commission 1,240 at 0.40%; editable
    "migration": {"alpha_transfer_fees": "500", "beta_transfer_fees_estimate": "1000"},
    "internal": {"servicing_cost": "9000", "onboarding_cost": "4000", "min_margin_pct": "25"},
    "optimized_swaps": [
        {
            "from": "ZZGEQLDRA013",
            "to": "ZZGLBEQI0014",
            "to_name": "Global Equity Index Fund I CHF",
            "to_ongoing": "0.20",
            "to_transaction": "0.05",
        },
        {
            "from": "ZZEMMKTA0019",
            "to": "ZZWLDEMETF10",
            "to_name": "Emerging Markets Index ETF",
            "to_ongoing": "0.18",
            "to_transaction": "0.08",
        },
    ],
}
