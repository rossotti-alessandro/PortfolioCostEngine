# Fee taxonomy

Status: research baseline, 2026-11-06. Machine-readable version: [`data/taxonomy/fee_taxonomy.csv`](../../data/taxonomy/fee_taxonomy.csv).
Sources are cited by `SRC-*` ids from [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md). Items marked **(to verify)** come from domain knowledge and were not confirmed against a primary text in this pass.

This replaces `docs/FEE_TAXONOMY.md` and `data/fee_taxonomy.csv` from the ChatGPT kit. The kit's 34 codes were a good start. The changes are listed in [`CRITICAL_REVIEW.md`](../CRITICAL_REVIEW.md) (findings F-10 to F-16).

## 1. The idea in one paragraph

A client pays for a portfolio in three ways. Some costs are **billed**: the bank debits the cash account (mandate fee, custody, brokerage). Some are **embedded**: they come out of a fund's NAV or a structured product's price, and the client never sees a debit (fund TER, issuer margin). Some are **implicit**: they hide in an execution rate (FX margin, bid/ask). A fair comparison has to cover all three, but each one has a different level of proof. The engine therefore tags every cost with *what it is* (category), *how we know it* (evidence status) and *how it is charged* (basis), and it never adds two numbers that describe the same money.

## 2. Ten layers (level 1)

| # | Layer | Who earns it | Typical evidence | Visible to client? |
|---|---|---|---|---|
| L1 | Service: management, advisory, all-in | Bank or asset manager | Mandate contract, fee advice, ex-post cost report | Yes, debit |
| L2 | Custody and account | Custodian bank | Tariff, fee advice, cash statement | Yes, debit |
| L3 | Explicit transaction costs | Bank, broker, exchange | Trade confirmations, transaction list | Yes, in the trade's net amount |
| L4 | Product, embedded (funds, ETFs) | Fund manager and service providers | KID, factsheet, annual report | No, inside NAV |
| L5 | Product, embedded (structured products) | Issuer and distributor | KID, termsheet, issuer cost data | No, inside price |
| L6 | Implicit execution costs | Bank or market | FX confirmations vs reference rate; quotes | No, inside rate |
| L7 | Insurance wrapper | Insurer | Policy, insurance KID, annual policy statement | Partly |
| L8 | Financing | Lender | Lombard agreement, interest advices | Yes, debit |
| L9 | Taxes and duties on costs and trades | State | Trade confirmations, fee invoices | Yes |
| L10 | One-off and switching | Old and new provider | Tariff, transfer quote, termination clause | Yes, once |

Two more ledgers sit *beside* the cost ledger, never inside the total:

- **Third-party compensation (retrocessions, trailer fees, distribution fees).** These are paid by product providers to the bank or manager. They are not an extra cost to the client, because they are already inside L4/L5. They matter for two reasons: they are a conflict of interest, and under Swiss case law they generally belong to the client unless validly waived (to verify, see `SRC-BDO-FINMA-RS`, F-14). If they are refunded to the client, the refund is a **credit** that lowers net cost.
- **Income and performance.** Dividends, coupons, returns. Out of scope for the cost total.

## 3. Level 2 categories

Each row is one `fee_code`. `basis` says how it is computed. `default_status` is the best status we can usually reach with normal client documents.

### L1 Service

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `MGMT_DISCRETIONARY` | Discretionary mandate fee | % p.a. of eligible assets, often tiered, often quarterly in arrears | Observed (fee advice) or Contractual | If the mandate is "all-in", custody and brokerage are inside: tag them `included_in` |
| `ADVISORY_FEE` | Advisory mandate fee | % p.a. or flat | Observed or Contractual | Usually replaces, not adds to, `MGMT_DISCRETIONARY` |
| `ALL_IN_FEE` | Flat fee covering management, custody and trading | % p.a. | Observed or Contractual | Parent of `CUSTODY_*`, `BROKERAGE_*` within its stated scope. Check the exclusion list (FX, third-party fees, stamp duty are usually excluded) |
| `PERFORMANCE_FEE_MANDATE` | Mandate performance fee | % of gain above hurdle / high-water mark | Observed only after the fact | Never forecast as certain |
| `PLATFORM_FIXED` | Fixed service or package fee | CHF per quarter / year | Observed or Contractual | May bundle `ACCOUNT_*` |
| `EAM_FEE` | Fee of an external asset manager billed via the bank | % p.a. | Observed | Safe Capital's own fee belongs here in the *proposed* scenario |

### L2 Custody and account

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `CUSTODY_FEE` | Safekeeping fee on securities | % p.a., tiered (cumulative bands or single rate), minimum per quarter or year, often on month-end average | Observed or Contractual | Child of `ALL_IN_FEE` if bundled |
| `CUSTODY_SURCHARGE` | Surcharge for foreign custody, precious metals, alternative funds, valueless positions | % or flat per position | Contractual | Often excluded from all-in |
| `ACCOUNT_FEE` | Account maintenance, statements, e-banking | Flat | Observed | |
| `PAYMENT_FEE` | Outgoing payments | Per payment | Observed | Usually immaterial; show, but out of comparison scope unless the proposal changes it |
| `REPORTING_FEE` | Tax statement, extra reports, bank confirmations | Flat | Observed | Same |

### L3 Explicit transaction costs

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `BROKERAGE` | Bank commission on securities trades | % of notional with minimum, bands by asset class | Observed (confirmation) | Child of `ALL_IN_FEE` if bundled |
| `TICKET_FEE` | Fixed fee per trade | CHF per trade | Observed | Alternative to `BROKERAGE` |
| `THIRD_PARTY_TRADING` | Exchange, foreign broker and settlement fees | Per trade | Observed | Usually excluded from all-in |
| `FUND_SUBSCRIPTION_BANK` | Bank's fee on fund subscriptions (separate from fund's own entry charge) | % of amount | Observed | Do not confuse with `FUND_ENTRY_CHARGE` |
| `FX_COMMISSION` | Explicit FX commission line | % of FX notional | Observed | If both a commission and a margin exist, they are different money; if the bank's rate already contains the margin, do not add an estimated margin on top |

### L4 Product, embedded (funds and ETFs)

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `FUND_ONGOING` | TER / ongoing charges / KID "management fees and other administrative or operating costs" | % p.a. of average holding value | Estimated (from exact share-class KID) | **Contains** `FUND_MGMT_FEE`. Never add both |
| `FUND_MGMT_FEE` | Management fee component (AMF) | % p.a. | Informational | Child of `FUND_ONGOING` |
| `FUND_TRANSACTION` | Portfolio transaction costs inside the fund | % p.a. (KID) | Estimated | **Not** in TER/OCF. In the PRIIPs KID it is a separate line (`SRC-PRIIPS-653`) |
| `FUND_PERFORMANCE` | Fund-level performance fee / carried interest | % p.a., incidental | Estimated (historical average) | Not in OCF |
| `FUND_ENTRY_CHARGE` | Fund's entry charge | % one-off, KID shows a *maximum* | Illustrative max | One-off. Actual may be waived |
| `FUND_EXIT_CHARGE` | Fund's exit charge | % one-off | Illustrative max | One-off |

### L5 Product, embedded (structured products)

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `SP_ENTRY_COST` | Issuer's entry cost = issue price minus fair value (includes issuer margin and any distribution fee) | % one-off | Estimated (issuer KID / cost data) | SSPA concept (`SRC-SSPA-COST`) |
| `SP_ONGOING` | Running fees, e.g. tracker management fee | % p.a. | Estimated | |
| `SP_EXIT_COST` | Exit cost if sold before maturity (bid/fair-value gap) | % one-off | Estimated, conditional | SSPA: usually zero if held to maturity |

### L6 Implicit execution costs

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `FX_MARGIN` | Spread between executed FX rate and a reference mid rate at execution time | % of FX notional | Estimated, only with timestamped confirmation + reference rate | Unknown if no confirmation. Never assume a "typical" margin as observed |
| `BID_ASK_SPREAD` | Market spread on securities | % of notional | Estimated | Market cost, not bank revenue. Show separately, exclude from the bank comparison by default |

### L7 Insurance wrapper

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `WRAPPER_ADMIN` | Policy administration / management charge | % p.a. of policy value | Observed (policy statement) or Contractual | **Adds** to the underlying fund costs |
| `WRAPPER_RISK` | Mortality / guarantee cost | % p.a. or premium | Contractual | |
| `WRAPPER_ENTRY` / `WRAPPER_SURRENDER` | Entry loading, surrender penalty | % one-off, by policy year | Contractual | One-off, scenario-specific |

### L8 Financing

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `LOMBARD_INTEREST` | Interest on securities-backed loan | % p.a. on drawn amount | Observed | Out of the portfolio cost total by default; show in a separate block |
| `COMMITMENT_FEE` | Fee on undrawn credit line | % p.a. | Contractual | Same |

### L9 Taxes and duties

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `VAT_ON_FEES` | Swiss VAT on fees | 8.1% of taxable fee | Observed | Applies to Swiss-domiciled clients; services to clients domiciled abroad are generally not subject to Swiss VAT (place-of-supply rule, to verify). Swissquote states VAT 8.1% on custody fees (`SRC-SQ-FEES`) |
| `STAMP_DUTY_CH` | Swiss securities transfer stamp duty (Umsatzabgabe) | 0.075% Swiss / 0.15% foreign securities per party, when a Swiss securities dealer is involved (to verify, `SRC-STG`) | Observed on confirmation | A tax, not provider revenue. It is the same at any Swiss bank, so it mostly cancels out in a like-for-like comparison |
| `FTT_FOREIGN` | Foreign transaction taxes (e.g. Italian/French FTT, UK stamp) | % of notional | Observed | Same logic |
| `WHT_UNRECLAIMED` | Withholding tax not reclaimed | % of income | Out of scope | Tax matter. Mention only if the proposal changes reclaim service |

### L10 One-off and switching

| fee_code | Meaning | Basis | Default status | Overlap rule |
|---|---|---|---|---|
| `TRANSFER_OUT` | Fee to transfer positions to another bank | CHF per position (e.g. Swissquote CHF 50 electronic, JB Lux EUR 100) | Contractual | One-off, only in the switching scenario |
| `LIQUIDATION_COST` | Cost of selling positions that cannot be transferred (brokerage + stamp + spread + taxes) | % of notional | Estimated | One-off |
| `EARLY_TERMINATION` | Mandate or product early exit penalty | Contract | Contractual | One-off |
| `CLOSING_FEE` | Account closure / compliance closure fee | Flat | Contractual | One-off |

### Credits (reduce net cost)

| fee_code | Meaning | Rule |
|---|---|---|
| `RETRO_REFUNDED` | Retrocession actually credited to the client | Counts only when a credit appears in the cash statement or ex-post report |
| `FEE_REBATE` | Negotiated rebate or discount credited | Same |

## 4. Evidence status (the second axis)

Every cost atom carries exactly one status. The dashboard colours and the totals both depend on it.

| Status | Meaning | Example | Counts in "proven cost"? | Counts in "estimated total"? |
|---|---|---|---|---|
| `OBSERVED` | We saw the actual charge for the client in the period | Fee advice: CHF 4,250 management fee Q3 | Yes | Yes |
| `CONTRACTUAL` | Computed from the client's own signed tariff and their assets | 0.25% custody × average assets | No | Yes |
| `ESTIMATED` | Computed from a public rate for the exact product (KID) and the client's holding | TER 0.07% × ETF value | No | Yes |
| `PUBLIC_TARIFF` | Computed from the bank's *published* list price, not the client's own tariff | Swissquote custody list price | No | Yes, flagged weak; private banks negotiate |
| `ILLUSTRATIVE` | A number from a KID example or a maximum | "Entry costs up to 3%" | No | No |
| `UNKNOWN` | A cost that probably exists but cannot be quantified | FX margin with no FX confirmations | No | No, shown as a gap with a document request |
| `NOT_APPLICABLE` | Confirmed absent | No structured products held | n/a | n/a |

Rule: an `UNKNOWN` is never zero. The dashboard shows a total *and* a coverage figure (share of assets and share of expected cost categories with evidence).

## 5. Basis and calculation rules

- **Tiered rates.** Contracts use either *cumulative bands* (each slice at its own rate, e.g. JB Lux custody 0.30% / 0.25% / 0.20% / 0.15%, `SRC-JB-LUX`) or a *single rate for the whole amount* once a threshold is reached. The contract decides; the engine must support both.
- **Minimums per period.** Minimums are often per quarter (JB Lux: EUR 360 per quarter). Apply the minimum per billing period, not per year.
- **Assets base.** Month-end average, quarter-end value or daily average. Record which. Exclusions (cash, precious metals, in-house funds) change the base.
- **Annualisation.** `annual = period_amount × 365 / days_in_period` only for recurring costs. One-off costs are shown separately and amortised only in a stated scenario (e.g. over 3 years).
- **Embedded product costs.** `estimated_cost = average_holding_value × rate × days/365`. Use the exact share-class ISIN and a KID dated within the period. A fuzzy name match is not enough.
- **Bps view.** `cost_bps = annual_cost_chf / average_assets_chf × 10,000`. State which assets (with or without cash, with or without loans).
- **Currency.** Convert at a recorded rate and date. Keep the original amount.
- **VAT.** Store fees net and VAT separately, so a VAT-exempt foreign client and a Swiss client are compared correctly.

## 6. Double-counting rules (hard checks in the engine)

1. `FUND_MGMT_FEE` is inside `FUND_ONGOING`. Never add both.
2. A KID "total costs" or "annual cost impact" figure already includes its components. Use components *or* total, never both.
3. Anything tagged `included_in = ALL_IN_FEE` is excluded from the sum, but kept for the breakdown view.
4. An `OBSERVED` charge and a `CONTRACTUAL` estimate of the same fee in the same period: keep the observed one, use the contractual one only to check it (and flag the gap if they differ by more than a tolerance).
5. A bank's annual ex-post cost report total and the sum of individual fee advices for the same year describe the same money. Reconcile, do not stack.
6. Retrocessions are not added as a cost. Only refunds to the client are credits.
7. Embedded product costs are already reflected in the fund's performance. Show them in the cost view; never subtract them again from a return figure.
8. Insurance wrapper costs and underlying fund costs *do* add up (two separate layers), provided both are evidenced.

## 7. Three totals the dashboard shows

| Total | Contents | Use |
|---|---|---|
| **Proven cost** | `OBSERVED` only | The number we can defend line by line |
| **Estimated all-in cost** | `OBSERVED` + `CONTRACTUAL` + `ESTIMATED` + `PUBLIC_TARIFF` | The headline economic cost, always shown with its coverage % |
| **Gaps** | List of `UNKNOWN` categories with the document that would close each one | The call to action for the meeting |

The comparison with Safe Capital uses the *estimated all-in cost* on both sides, on the **same holdings**. A second, separately labelled scenario may show a *different* proposed portfolio. One-off switching costs are shown apart, with payback in months.

## 8. Mapping from the kit

| Kit code | New code | Note |
|---|---|---|
| `MANAGEMENT_ADVISORY` | `ADVISORY_FEE` / `MGMT_DISCRETIONARY` | Split, since they replace each other |
| `CUSTODY_SAFEKKEEP` (typo) | `CUSTODY_FEE` | |
| `OCF_TOTAL` | `FUND_ONGOING` | Renamed: Swiss documents say TER, KIDs say ongoing costs |
| `FUND_MANAGEMENT_SUBSET` | `FUND_MGMT_FEE` | |
| `FUND_TRANSACTION_INTERNAL` | `FUND_TRANSACTION` | |
| `STRUCTURED_ISSUER_MARGIN`, `STRUCTURED_ADMIN`, `STRUCTURED_REBALANCE` | `SP_ENTRY_COST`, `SP_ONGOING` | Aligned to the SSPA cost concept; rebalancing fees fold into ongoing |
| `SWISS_STAMP` | `STAMP_DUTY_CH` | |
| `THIRD_PARTY_REBATE` | `RETRO_REFUNDED` + side ledger | Separated: received vs refunded |
| (missing) | `ALL_IN_FEE`, `EAM_FEE`, `FUND_SUBSCRIPTION_BANK`, `TICKET_FEE`, `REPORTING_FEE`, `CLOSING_FEE`, `LIQUIDATION_COST`, `PUBLIC_TARIFF` status | Added |
