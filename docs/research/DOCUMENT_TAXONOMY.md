# Document taxonomy

Status: research baseline, 2026-11-06. Machine-readable version: [`data/taxonomy/document_types.csv`](../../data/taxonomy/document_types.csv). Source ids refer to [`SOURCE_REGISTER.md`](SOURCE_REGISTER.md).

## 1. What a prospect usually brings

A prospect rarely has a neat "cost report". In practice they bring whatever their bank sends them: a year-end portfolio statement, some quarterly fee advices, a tax statement, maybe a contract. The engine has to work with any subset, say clearly what each document can and cannot prove, and ask for the missing piece that matters most.

Ranked by value for the cost analysis:

| Rank | Document | Why it matters | What it cannot prove |
|---|---|---|---|
| 1 | **Annual cost and fee statement** (ex-post) | One document with service and product costs for the year. The best single source | Often only on request in Switzerland (see §3). Format differs per bank |
| 2 | **Portfolio / asset statement** (Vermögensausweis, estratto patrimoniale) | Holdings: ISIN, quantity, value, currency, date. Base for every embedded-cost estimate | No fees. UBS's own guide says quarterly account fees are not in the securities transaction list (`SRC-UBS-GUIDE`) |
| 3 | **Fee advices / debit notes** (avviso di addebito) | Observed management, custody, all-in fees for a period, with VAT | Product costs; FX margins |
| 4 | **Mandate or advisory contract + fee schedule** | The client's own rates, tiers, minimums, what "all-in" includes | Whether the bank actually billed that |
| 5 | **Cash account statements** (12 months) | Every debit, including fees not in other documents | Embedded costs |
| 6 | **Transaction list / trade confirmations** | Brokerage, third-party fees, stamp duty, FX rates per trade | Contract terms |
| 7 | **KIDs / factsheets of held products** | Exact-class ongoing, transaction and performance costs. Usually public, so we fetch them; the client need not bring them | What the client actually paid (KID amounts are illustrations) |
| 8 | **Structured product termsheets** | Product terms; KID gives entry cost | Issuer margin unless in KID/cost data |
| 9 | **Insurance policy statement** (for wrappers) | Wrapper charges, surrender values | Underlying fund costs |
| 10 | **Tax statement** (Steuerauszug / estratto fiscale) | Year-end values, income, sometimes fees listed for deduction | Fee completeness |
| 11 | **Lombard / credit agreement** | Financing costs | Portfolio costs |

## 2. Classification fields for every uploaded file

`institution` · `booking_entity` · `booking_country` (a Julius Baer Luxembourg tariff is not a Zurich one) · `client_reference` (pseudonymised) · `account_ids` · `document_type` · `period_start` / `period_end` or `as_of_date` · `reporting_currency` · `language` (de / fr / it / en) · `number_format` (Swiss `1'234.50` vs Italian `1.234,50`) · `is_scanned` · `page_count` · `sha256` · `duplicate_of` · `actual_vs_illustrative`.

## 3. Swiss specifics that change the design

- **Cost reporting is often on request in Switzerland.** Under the Financial Services Act (FinSA), providers must give account of costs, but the duty to report in detail is framed largely "on request" (FinSA Art. 16 para. 2, *to verify against the official text*; Fedlex did not render for us). EU banks under MiFID II send an annual ex-post cost report by default (`SRC-ESMA-QA`). Many Swiss banks send one voluntarily, but not all. **Consequence:** the "document request" output should include a ready-to-sign letter asking the bank for a full cost and retrocession statement for the last 12 months. That letter is also a strong sales tool.
- **Retrocessions.** A detailed statement of third-party compensation must be provided free of charge on request (FINMA conduct circular as summarised by BDO, `SRC-BDO-FINMA-RS`). Ask for it in the same letter.
- **Languages.** Lugano prospects bring Italian, German and English documents, and Italian residents bring Italian bank and insurance documents (*estratto conto titoli*, *rendiconto annuale dei costi e oneri* under MiFID II, *polizza unit-linked* statements). The taxonomy has Italian labels for this reason.
- **Number formats.** Swiss documents use the apostrophe thousands separator (`1'500'000.00`, as in the kit's fictitious statement). Italian documents use `1.500.000,00`. The parser must detect locale per document, not per user.
- **Bond prices** are quoted in % of nominal; quantity is a nominal amount. Value = nominal × price% (+ accrued interest, shown separately or not).
- **Structured feeds.** Some banks deliver SWIFT MT535 (holdings), MT536 (transactions), MT940 (cash), MT590 (charges), or proprietary CSV/XML to authorised external asset managers (`SRC-UBS-PSN`, `SRC-LGT-PRO`). Safe Capital, as an external asset manager, may get such feeds for its *own* clients, but not for prospects. For prospects, PDF upload is the realistic path.

## 4. Document types

See the CSV for the full list with extraction targets. Summary by family:

| Family | Types |
|---|---|
| Holdings | `portfolio_statement`, `consolidated_report`, `tax_statement` |
| Cash | `cash_statement`, `interest_advice` |
| Trading | `trade_confirmation`, `transaction_list`, `fx_confirmation`, `corporate_action_notice` |
| Fees | `annual_cost_report`, `fee_advice`, `retrocession_statement` |
| Contracts | `mandate_contract`, `advisory_contract`, `custody_tariff`, `general_price_list` |
| Products | `kid_priips`, `kid_finsa`, `factsheet`, `prospectus`, `annual_report_fund`, `sp_termsheet` |
| Wrappers and credit | `insurance_policy_statement`, `insurance_kid`, `lombard_agreement` |
| Proposal (Safe Capital side) | `proposal_tariff`, `proposal_custodian_tariff`, `proposal_portfolio`, `transfer_quote` |
| Other | `performance_report`, `unknown` (goes to manual review) |

## 5. Request planner (what to ask for next)

The engine scores missing documents by the cost they would unlock (in CHF), not by a fixed order. Typical states:

| What we have | What we can show | Ask next |
|---|---|---|
| Portfolio statement only | Allocation; embedded product costs (estimated); custody/mandate only from public tariffs (weak) | Fee advices or annual cost statement; contract |
| + fee advices for 4 quarters | Observed service and custody fees | Transaction list (brokerage, FX); retrocession statement |
| + contract | Check bank billed what the contract says | FX confirmations if many foreign-currency trades |
| + annual cost statement | Near-complete picture; reconcile with the rest | Nothing critical; confirm all-in scope |

Each request carries: document name in the client's language, why it matters, the CHF range it could affect, and which dashboard figures stay "estimated" without it.
