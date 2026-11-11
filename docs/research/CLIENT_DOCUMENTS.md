# Documents a private wealth client holds, and which ones we can test on

This page answers three questions. Which documents does a typical Swiss or Italian private client receive
about their portfolio? Which of them are public, so we can collect real copies? For the ones that
are not public, how do we test FeeLens without client data? The live coverage numbers are in
[`data/specimens/COVERAGE.md`](../../data/specimens/COVERAGE.md). Taxonomy codes are those in
`data/taxonomy/document_types.csv`.

## 1. The client's document set

A client with a bank mandate or advisory relationship usually holds the following, roughly in order of
how useful each is for a cost analysis:

| # | Document | Taxonomy code | Who issues it | How often | Public? | What FeeLens takes from it |
|---|---|---|---|---|---|---|
| 1 | Portfolio / asset statement (Vermögensausweis, estratto patrimoniale) | `portfolio_statement` | custodian bank | monthly/quarterly | **No** | positions, ISINs, values: the base of every % |
| 2 | Annual costs and charges report, ex-post (MiFID II; in CH on request under FinSA) | `annual_cost_report` | bank | yearly | **No** | service costs, product costs, inducements, in CHF/EUR and % |
| 3 | Fee advice / debit notes (Gebührenbelastung) | `fee_advice` | bank | quarterly | **No** | observed custody, mandate and advisory fees |
| 4 | Cash account statement (Kontoauszug, estratto conto) | `cash_statement` | bank | monthly | **No** | every billed debit, including fees |
| 5 | Trade confirmations, transaction list | `trade_confirmation`, `transaction_list` | bank/broker | per trade | **No** | brokerage, third-party fees, stamp duty, FX |
| 6 | Mandate or advisory contract, individual tariff | `mandate_contract`, `advisory_contract`, `custody_tariff` | bank | once, amended | **No** (templates sometimes public) | agreed rates, tiers, minimums, all-in scope |
| 7 | Tax statement (Steuerauszug, e-Steuerauszug) | `tax_statement` | bank | yearly | **No** (standard specimens exist) | year-end values, income, sometimes fees |
| 8 | Bank's public price list | `general_price_list` | bank | yearly | **Yes** | list prices, used when the individual tariff is missing |
| 9 | FinSA / MiFID ex-ante cost brochure | `cost_disclosure` (proposed code) | bank | when rates change | **Yes** | standard cost rates per service |
| 10 | Fund / ETF KID (PRIIPs or Swiss FinSA BIB) | `kid_priips`, `kid_finsa` | fund manager | monthly–yearly | **Yes** | ongoing, transaction, performance, entry/exit costs per ISIN |
| 11 | Fund factsheet | `factsheet` | fund manager | monthly | **Yes** | TER/OCF cross-check |
| 12 | Prospectus, annual report of the fund | `prospectus`, `annual_report_fund` | fund manager | yearly | **Yes** | maximum fees, historical TER, performance fee actually charged |
| 13 | Structured product termsheet and KID | `sp_termsheet`, `kid_priips` | issuer | once | **Yes** | distribution fee, issuer margin if stated, payoff |
| 14 | Insurance policy statement | `insurance_policy_statement` | insurer | yearly | **No** | wrapper charges, surrender value |
| 15 | Insurance-based product KID, Italian DIP aggiuntivo IBIP | `insurance_kid` | insurer | yearly | **Yes** | wrapper cost rates, cost per investment option |
| 16 | Lombard credit agreement, interest advice | `lombard_agreement`, `interest_advice` | bank | rare | **No** | financing cost |
| 17 | Performance report | `performance_report` | bank/manager | quarterly | **No** | performance only, no costs |

The documents that show what the client **actually paid** (rows 1–7, 14) are all private. The public
documents (rows 8–13, 15) give **rates**, not amounts. That is why FeeLens needs both: the client's own
statements for the base and the billed fees, and public product documents for the costs embedded in
funds and products.

## 2. Is "several hundred real documents" realistic?

Yes, for the public families. Every UCITS fund and ETF share class sold to retail investors in the EU
must have a KID, so there are hundreds of thousands. Each Swiss and Italian bank publishes a price list
or Foglio Informativo, and issuers publish thousands of termsheets. The limits are:

- **Template diversity, not count.** Fifty iShares KIDs share one layout. The corpus is built to
  maximise distinct issuers and layouts per family and language, not files.
- **Access rules.** robots.txt, login walls and country gates are respected. UBS, Credit Suisse and
  BancaStato are excluded. Some managers (Pictet, Vontobel, Fidelity) block plain downloads.
- **Copyright.** PDFs are never committed. The manifest re-downloads them and checks their hashes.

## 3. The private documents: synthetic look-alikes

Real client documents can never enter the repo (`.claude/rules/privacy.md`). For rows 1–7 and 14 we use
synthetic documents that copy the **layout archetype** under invented institution names marked SYNTHETIC.
The demo thread already generates two prospects (`backend/src/pce/demo/generate.py`, `archetypes.py`).
To reach the template diversity of the public corpus, the plan is:

1. **Archetype catalogue.** For each private document type, list the layout families seen in the market:
   Swiss private bank (multi-currency, CHF base, asset-class blocks), Swiss cantonal or retail bank
   (single table), Italian bank (comma decimals, "Controvalore", ex-post report with inducements),
   German Depotauszug, Luxembourg private bank, US-style broker activity statement, insurance policy
   statement. Use the public specimens that the samples slice collects as layout references only.
2. **Parameterised generator.** A single generator renders each archetype from a YAML spec: language,
   number format (1'234.56 / 1.234,56 / 1,234.56), currency, column order, page breaks, footnotes,
   multi-page tables and scanned or skewed variants (rasterise, add noise, rotate 0.5–2°). Every
   number comes from a ground-truth JSON that is written alongside the PDF, so extraction can be scored
   exactly.
3. **Real public instruments inside.** Holdings use real ISINs from this corpus. That lets the KIDs in
   the corpus resolve product costs end to end, while the client side stays fictitious.
4. **Volume.** About 8 archetypes × 4 languages × 3 variants (clean, scanned, messy) gives about 100
   private-type documents with exact ground truth. That is enough to measure position and fee recall per
   archetype.
5. **Pilot reality check.** Synthetic layouts are guesses until checked against real statements. During the
   pilot (SC-11.1), the analyst runs real statements locally and reports layout misses as new
   archetypes, without the documents leaving the machine.

This plan belongs to SC-9.1 (synthetic golden corpus); it is proposed here, not built.
