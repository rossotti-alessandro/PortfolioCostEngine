# Complete portfolio cost protocol and FeeLens gap analysis

Status: research and design, 2026-11-25 (SC-2.4). Reviewed against `main` at commit 91181df. Engineering
view, not legal or tax advice. Tax rates and practitioner durations below are indicative and marked to
verify; they go through `SOURCE_REGISTER.md` before any client sees them. Reader copy with the same content:
the Claude Doc "FeeLens complete portfolio cost protocol" (project thread "Design complete portfolio cost protocol").

Related: [FEE_TAXONOMY.md](FEE_TAXONOMY.md) (layers L1-L10, evidence statuses, double-counting rules),
`INSTRUMENT_DATA_SOURCES.md` (source survey, SC-9.8 branch), [DOCUMENT_TAXONOMY.md](DOCUMENT_TAXONOMY.md).

## Executive summary

FeeLens measures the costs a bank writes down, not yet all the costs a family pays. Explicit bank fees and
fund running costs are handled well and honestly: missing is never zero and nothing is counted twice. What is
missing is the second half: costs driven by trading (FX margins, spreads, stamp duties), costs hidden in cash
and products (low cash interest, fund trading costs, structured product margins), and a way to fill gaps
from trusted outside data with a score on every number.

**The protocol in one line:** collect a fixed document set per bank, build one book of accounts, positions
and transactions, attach every cost to a position or an account, fill each cost from the best source in a
fixed order, cross-check it against a second source, score it, and show three totals (proven, estimated,
implicit range) plus the gaps.

**The ten gaps that matter most, in order of impact** (details in section 5):

1. The expected-cost checklist is too short: per bank only service, custody and brokerage are expected, so a
   report can look complete when FX margin, fund trading costs, stamp duty, VAT or structured costs were never examined.
2. The bank's ex-post product-cost total is only a cross-check; with no KID the product cost stays unknown.
3. Repeated cash debits of the same fee collapse into one (reproduced: 4 x CHF 500 gives CHF 500 observed).
4. No transaction ledger: trading-driven costs can be neither estimated nor reconciled.
5. No book of record: accounts, instruments, positions and transactions are rebuilt from loose facts each run.
6. One source per figure, no source tier, no confidence score.
7. Instrument type guessed from the name (SC-6.1 fixes it with ISIN reference data).
8. Base currency fixed to CHF; only FX rates printed on the client's papers are used.
9. Product costs on current value instead of average value; printed average assets unused.
10. Taxonomy lacks derivatives, private markets, hedge funds, crypto, securities lending, cash drag, hedged
    classes, bond mark-ups and a MiFID category column.

Gaps 1-3 and 9 are small local fixes. Gaps 5-6 are the foundation.

**Decisions (Ale, 2026-11-25):** ISIN-only lookups to public registers are approved (live: SC-6.3, PR #70;
ECB/SNB reference rates follow the same rule, no client data). Implicit costs are shown as a separate range
and never added to the headline totals. Done since: gap 3 (SC-7.7, PR #66), gap 7 (SC-6.3), gap 1 (SC-7.8).

## 1. The analyst's job today, and the documents it needs

By hand, a full cost review of one family with 2 to 4 banks takes roughly one to two working days and usually
stops at explicit fees plus fund TERs (practitioner estimate, to confirm with Safe Capital).

### How it is usually done

1. **Collect.** The prospect signs a request or forwards PDFs; the analyst chases missing years, accounts and the cost report.
2. **Consolidate.** Positions from each bank go into one spreadsheet, converted to one currency at one date.
3. **Look up products.** Each fund ISIN is checked on Morningstar, fundinfo or Bloomberg for its TER.
   Structured products are usually skipped or given a rule-of-thumb margin.
4. **Apply the tariff.** The price list or mandate is applied to the assets: management, custody, ticket fees.
5. **Read the ex-post report.** If one exists (mandatory in the EU, on request in Switzerland), its totals are copied as given.
6. **Sum and compare.** Totals in CHF and in % of assets, next to the proposal.

Typical weaknesses: the management fee is added on top of a TER that already contains it; the bank report is
trusted without checking it against the debits; average versus year-end assets is not stated; FX margins,
spreads and cash drag are left out; unknown fees silently become zero; the work is not reproducible.

At large banks and consultants the same job runs on data feeds: the bank's core system (Avaloq, Temenos) for
its own fees, EMT files from fundinfo or WM Datenservice for product costs, and a transaction cost analysis
(TCA) tool for execution. Fee-audit firms add a review of FX rates applied against a reference fixing. Better
data, but each source is still trusted alone and rarely scored.

### The document set per family

A typical family has 2 to 5 custodian banks, 1 to 3 mandates, often an insurance wrapper and sometimes
private-market commitments: about 30 to 150 documents per year.

| Document (per bank, per year unless stated) | Typical count | What it unlocks | Priority |
| --- | --- | --- | --- |
| Statement of assets, start and end of year | 2 (or 4 quarterly) | Positions, values, average assets, reconciliation | Must |
| MiFID / FinSA ex-post cost report | 1 | Service, transaction, ancillary and product costs as the bank sees them; inducements | Must |
| Mandate or advisory contract with individual tariff | 1 | Agreed rates, tiers, minimums, what an all-in fee includes | Must |
| Transaction list for the year | 1 (or many trade confirms) | Turnover, brokerage, stamp duty, FTT, FX volume | Must for trading costs |
| Fee advices / debit notes | 4 to 12 | Proof the fee was charged | High |
| Cash account statements | 12 | Debits, credited interest (cash drag), retrocession refunds | High |
| FX confirmations | 0 to 100 | Rate applied, so the FX margin can be measured | High if FX is traded |
| KID (PRIIPs or FinSA) or EMT row, per fund or product | 1 per ISIN | Exact share-class running, transaction, entry, exit, performance costs | Must per fund |
| Structured product termsheet or KID | 1 per ISIN | Issuer margin, running fee, exit cost | Must per product |
| Tax statement | 1 | Withholding tax reclaimed or lost, stamp duty totals | Medium |
| Bank public price list (dated, right legal entity) | 1 | Fallback when there is no individual tariff | Medium |
| Retrocession / inducement statement (Art. 26 FinSA, on request) | 1 | Amounts the bank kept from product providers | Medium |
| Insurance policy statement and contract | 1 | Wrapper charges, surrender penalties | If a wrapper exists |
| Private fund capital account statements, capital calls, LPA | 4 + calls | Management fee on commitment, carry, fund expenses | If alternatives exist |
| Lombard / credit agreement and interest advices | 1 + 4 | Financing cost (shown apart) | If credit exists |

**Minimum viable pack** to ask for first: per bank two statements, the ex-post cost report, the contract or
tariff and the transaction list; plus one KID per fund. What stays open with it is mainly FX margin and
spreads, which need trade-level FX data.

## 2. A complete cost taxonomy for every asset class

Keep the ten layers of FEE_TAXONOMY.md, and tag every cost on three more axes so that any asset class fits
and nothing is counted twice.

### Three axes every cost atom should carry

| Axis | Values | Why |
| --- | --- | --- |
| Regulatory category (MiFID II Annex II, mirrored by FinSA) | one-off, ongoing, transaction, ancillary, incidental; service vs product; third-party payments received | Lines up with EU ex-post reports and EMT fields, so a bank report reconciles line by line |
| Visibility | billed, embedded (NAV or price), implicit (rate or spread), tax, credit | Where to look for evidence and how to estimate |
| Payee | bank, manager, product issuer, market (spread), state (tax) | Separates provider revenue from market friction; spreads and taxes must not inflate a saving |

### Costs by asset class

Entries marked * are not in `fee_taxonomy.csv` today.

| Asset class | Explicit (billed) | Embedded in product | Implicit and taxes |
| --- | --- | --- | --- |
| Cash and deposits | account fee, negative interest charged* | sweep or money-market fund fee* | cash drag: credited rate below SARON / ESTR / SOFR* |
| FX | explicit FX commission | hedging cost in hedged share classes* | FX margin vs reference fixing, FX on dividends and coupons* |
| Listed equities | brokerage, ticket, third-party and exchange fees, custody, ADR depositary fees*, corporate action and dividend collection fees* | none | bid/ask spread, market impact*, stamp duty and FTT, unreclaimed withholding tax |
| Bonds | brokerage or none, custody | none | dealer mark-up inside the price*, new-issue selling concession* |
| Funds and ETFs | bank subscription fee | ongoing costs (TER/OCF incl. management fee), portfolio transaction costs, performance fee, entry/exit charges, securities lending revenue kept by the agent*, swap fee in synthetic ETFs* | ETF spread and premium/discount*, fund-of-funds double layer* |
| Structured products | brokerage | issuer margin (price minus fair value), running fee, early exit cost | secondary-market spread |
| Listed derivatives | commission per contract, exchange and clearing fees, give-up fees* | none | spread, roll cost*, interest on margin vs collateral returned* |
| OTC derivatives, FX forwards | arrangement fee* | none | spread inside forward points or premium* |
| Hedge funds | subscription fee | management fee, performance fee with high-water mark and hurdle, fund expenses, equalisation* | gating or redemption penalties* |
| Private equity, debt, real estate funds | placement fee* | management fee on commitment, carried interest, fund expenses, transaction and monitoring fees, feeder layer* | cost of uncalled capital* |
| Crypto | custody, trading commission, network fees* | ETP running fee* | spread, staking commission* |
| Insurance wrappers | admin, risk, entry loading, surrender penalty | underlying fund costs (they add up) | none |
| Credit (Lombard) | interest, commitment fee | none | shown apart, never in investment cost |
| Mandate, all-in, external manager | management, advisory, all-in, EAM, performance fee, family-office retainer or reporting fee* | none | retrocessions kept by provider (shown, not added) |

### Taxes and duties (indicative, to verify)

| Tax | Applies to | Indicative rate | Cost or neutral? |
| --- | --- | --- | --- |
| Swiss securities transfer stamp duty | trades through a Swiss securities dealer | about 0.075% per side Swiss, 0.15% foreign | Client cost, but charged at any Swiss bank: neutral in same-holdings comparison |
| UK stamp duty / SDRT | UK shares bought | about 0.5% | Same |
| French, Italian, Spanish FTT | large-cap domestic shares bought | about 0.1% to 0.4% | Same |
| US SEC fee | US share sales | a few cents per thousand | Same |
| Swiss VAT on fees | fees to Swiss-domiciled clients | 8.1% | Follows the client's domicile, not the bank |
| Unreclaimed withholding tax | dividends and coupons not reclaimed to treaty rate | treaty dependent | Real loss; only from the tax statement |

### Rules that keep the taxonomy honest

- One atom per economic cost, many evidences (report line, debit and tariff calculation of the same fee).
- Parents and children: management fee inside TER, custody inside all-in, issuer margin inside a structured
  product price; fund trading costs are outside TER. A child is shown, never added.
- Not a cost: option premiums, accrued interest paid on purchase, dividends, performance. Dividend yield is
  context, never netted.
- Spreads and taxes are shown, but a saving claim counts only costs the proposal changes.

## 3. Hybrid sourcing: documents first, databases second, every number scored

Outside data fills and checks; it never overrules the client's own documents.

### Source tiers

| Tier | Source | Example | Base score | Status |
| --- | --- | --- | --- | --- |
| T1 | Charge on the client's own papers | debit advice, cash debit, ex-post report line | 95 | observed |
| T2 | Client's signed contract or individual tariff on a verified base | mandate 0.80% on average assets | 85 | contractual |
| T3 | Issuer disclosure for the exact share class, dated in period | EMT row, PRIIPs or FinSA KID | 85 EMT, 80 KID | estimated |
| T4 | Bank aggregate for the client | ex-post product-cost total, average assets | 75 | estimated, portfolio level |
| T5 | Licensed database by ISIN | fundinfo, Morningstar, SIX | 65 | estimated |
| T6 | Bank public price list, right entity and date | Swiss bank tariff PDF | 60 | public_tariff |
| T7 | Reference-data model | FX margin vs ECB/SNB fixing; spread from venue data | 50 with trade data, 30 without | implicit estimate |
| T8 | Analyst assumption | typical bond mark-up band | 20 | illustrative, never in a headline |

FIRDS, OpenFIGI and GLEIF identify instruments (type, currency, share class); they give no costs and are not
a tier, but a confirmed identification is required for a full score.

### Confidence score

Start from the tier base score and apply in order; cap at 99. Only a person's confirmation marks a figure verified.

| Adjustment | Points |
| --- | --- |
| ISIN and share class confirmed by reference data | 0; name-only match capped at 40 |
| Document date outside the cost period | -10 per year |
| Rate without a stated base | -15 |
| Corroborated by an independent tier within tolerance | +10 |
| Conflict with another tier beyond tolerance | -20 and a review point |
| Extraction confidence below threshold | -10 to -30 |
| Confirmed by a person (four-eyes) | verified |

Bands: 85+ Strong, 65-84 Supported, 40-64 Indicative, below 40 out of the totals and shown as a range only.
Weights are a proposal to calibrate on the gold set before any client sees a score.

### Conflict rules

1. Specific beats general (client contract over price list; exact share class over fund family).
2. Observed beats computed for the same period; the computed figure becomes the cross-check.
3. Never average two sources; keep the loser as evidence and show the difference.
4. Tolerance before a flag: rates 2 bps or 5% relative; amounts CHF 1 or 2%.
5. Same tier, different values: no automatic pick, review with both values.
6. Newer within the period beats older; a document dated after the period only if nothing earlier exists, with a penalty.
7. Missing is not zero at every tier; only an explicit statement makes a cost not applicable.

Privacy: every outside lookup sends the ISIN only, to an allowlisted host, behind the off-by-default switch
and the egress guard (`.claude/rules/privacy.md`, ADR 0004). Needs Ale's per-PR approval.

## 4. The protocol, step by step

Key change: build the list of costs that must exist from what the family holds and does, then fill it.

1. **Scope.** Family, entities, accounts, 12-month cost period, base currency, tax domicile.
2. **Collect** the minimum pack per bank; request letter incl. FinSA Art. 26 statement; expected-vs-received inventory.
3. **Extract with evidence** (page + bbox or sheet + cell), as today.
4. **Book of record.** Entities, accounts, positions at start and end, transactions, cash flows. Reconcile:
   positions to statement total; start + flows + performance = end; cash debits to fee report.
5. **Identify instruments.** Check digit, then FIRDS / OpenFIGI for CFI type, currency, share class, hedged.
6. **Expected-cost checklist.** Per account (service, custody, account, reporting), per position by
   instrument type, per transaction (brokerage, third-party, tax, FX), per cash balance. Every row starts unknown.
7. **Fill from the tiers**, keeping every candidate value.
8. **Cross-check and score**; over-tolerance becomes a review point.
9. **Implicit costs** only with a stated method and data; otherwise unknown with a labelled typical range.
10. **Aggregate.** Inclusion graph, annualise by days, divide by average assets in scope. Proven, estimated
    all-in and implicit range, plus coverage (assets with product costs evidenced, checklist rows filled,
    value-weighted confidence).
11. **Human review.** Four-eyes on figures below 65 or above materiality, and on every client-report figure.
12. **Compare** on the same holdings and assumptions; taxes and spreads neutral unless the proposal changes
    them; switching costs one-off with payback.
13. **Report and learn.** Client report without internal margin; analyst pack with evidence; tariffs and
    product data cached in the catalog; accuracy tracked on the gold set.

### Implicit-cost methods

| Cost | Method | Data needed | Without the data |
| --- | --- | --- | --- |
| FX margin | (applied rate - reference mid at trade time) x amount | timestamped FX confirmations; ECB/SNB rates | unknown, typical band as range |
| Equity and ETF spread | half quoted spread x traded amount | transaction list; venue quotes | unknown, range by size band |
| Bond mark-up | execution price - evaluated price on trade date | transaction list; evaluated prices (paid) or TRACE (US) | unknown, range by issuer type |
| Cash drag | (reference rate - credited rate) x average cash | cash statements; SARON / ESTR / SOFR | unknown |
| Structured product issuer margin | issue price - fair value | issuer KID or termsheet; SSPA data | unknown, never a rule of thumb in a total |
| Fund trading costs | KID or EMT transaction cost | KID or EMT | unknown |
| Hedged share class | hedged vs unhedged class KID | both KIDs | inside the class TER; no extra estimate |
| Securities lending kept by agent | fund annual report revenue split | annual report | information only, already in fund return |

A range is never added to the proven or estimated totals.

## 5. FeeLens gap analysis, ranked by impact

The engine's rules are right; its inputs are too narrow. Gap 3 was reproduced with a synthetic test on
2026-11-25; the others are from reading the code at 91181df.

Already good: unknown is `None` and makes totals "at least"; inclusion graph and corroboration tested;
tariffs check jurisdiction and dates with tiers, minimums and proration; KIDs join by exact ISIN; KID
examples and maxima never counted; bank-reported product costs reconciled; retrocessions shown, not added;
internal margin kept out of the client payload.

| # | Gap | Where | Impact | Effort | Story |
| --- | --- | --- | --- | --- | --- |
| 1 | Expected-cost checklist has 3 items per bank; FX margin, fund transaction costs, stamp duty, VAT, structured costs, cash interest never become UNKNOWN, so `is_complete` can be true while layers are unexamined | `analysis.py:38` `SERVICE_CORE` | High | Small | SC-7.8 (done) |
| 2 | Bank ex-post product-cost total used only as cross-check; no KID means product cost unknown | `analysis.py:921` | High | Small | SC-7.9 (done: KIDs stay counted, the unexplained rest of the bank figure is added once) |
| 3 | Same-fee debits in one cash statement collapse: later ones become corroborating; with no period word the single debit counts as observed annual. 4 x CHF 500 gives CHF 500 | `analysis.py:508-509` | High | Small | SC-7.7 (done, PR #66) |
| 4 | No transaction table or parser for transaction lists | `db.py`, `extraction/parsers.py` | High for active portfolios | Medium | SC-7.12 |
| 5 | No Account / Instrument / Position / Transaction tables; holdings are dicts rebuilt from facts; atoms carry no currency or period | `db.py` | High | Large | SC-7.12 |
| 6 | One source per figure, no tier, no score | `finance/ledger.py` `FeeAtom` | High | Medium | SC-7.13 |
| 7 | Asset class from the name | `analysis.py:73` `infer_asset_class` | High | Medium | SC-6.3 (done, PR #70) |
| 8 | `BASE_CCY = "CHF"` ignores `Prospect.base_ccy`; only printed FX rates convert | `analysis.py:32`, `:261` | Medium-high | Small | SC-7.11 |
| 9 | Product cost = current value x rate (taxonomy says average value x rate x days/365); `meta:average_assets` parsed, unused | `finance/scenarios.py:192`, `extraction/parsers.py:619` | Medium | Small | SC-7.10 |
| 10 | Taxonomy lacks asset classes above and a MiFID category column | `data/taxonomy/fee_taxonomy.csv` | Medium | Small | SC-2.5 |
| 11 | No cost period on atoms | `FeeAtom` | Medium | Small | SC-7.10 |
| 12 | `finance.md` lists 6 statuses, `Measurement` has 8 | `.claude/rules/finance.md`, `ledger.py:24` | Low | Trivial | SC-2.5 |

### Data model sketch

- **Entity** (person, company, trust) 1-n **Account** (bank, booking entity, jurisdiction, mandate type, base currency).
- **Instrument** master by ISIN: CFI type, currency, share class, hedged, distributing, issuer LEI, sources
  and dates. Public data only, shared across tenants.
- **Position**: account, instrument, date, quantity, value in currency and base, FX rate and its source.
- **Transaction**: account, instrument, trade date, side, amount, price, confirmation fees, FX rate applied.
- **CostClaim**: one row per source stating a cost: fee code, regulatory category, rate or amount, basis,
  period, tier, evidence, extraction confidence.
- **CostAtom**: resolved cost per checklist row: winning claim, other claims, score, status, parent, period, denominator.

All tables except Instrument are tenant- and prospect-scoped, with an isolation test.

## 6. Backlog and decisions

| Order | Story | Gap | Size | Needs Ale's approval |
| --- | --- | --- | --- | --- |
| 1 | SC-7.7 Sum repeated fee debits per period | 3 | Small | Yes, totals change |
| 2 | SC-7.8 Expected-cost checklist | 1 | Small-medium | Yes |
| 3 | SC-7.12 Book of record | 4, 5 | Large | Shared contract (db) |
| 4 | SC-7.13 Cost claims and confidence score | 6 | Medium | Yes |
| 5 | SC-7.9 Ex-post product cost fallback | 2 | Small | Yes |
| 6 | SC-7.10 Average-asset denominator and period | 9, 11 | Small | Yes |
| 7 | SC-7.11 Base currency and reference FX | 8 | Small | Yes, external call |
| 8 | SC-6.1 Instrument resolver by ISIN | 7 | Medium | Yes, external call |
| 9 | SC-2.5 Taxonomy extension | 10, 12 | Small | Yes, taxonomy |
| 10 | SC-7.14 Implicit costs | implicit | Medium | Yes |

Open decisions for Ale: source tiers and score bands as a starting point; whether private markets are in pilot scope; ask
Massimo for manual-review time and usual document set.
