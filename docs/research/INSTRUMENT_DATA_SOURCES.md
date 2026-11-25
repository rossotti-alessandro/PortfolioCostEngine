# Instrument and product-cost data sources (ISIN → what it is → what it costs)

Status: research, 2026-11-25 (SC-9.8). Prices are list prices seen on public pages or typical quotes; confirm
in writing before any contract. Engineering view, not legal advice. Privacy rule: every lookup sends the ISIN
only, never a quantity, value, name or account (`.claude/rules/privacy.md`, ADR 0004).

## What the engine does today (main, 2026-11-25)

| Question | Today | Gap |
|---|---|---|
| ISIN found on a statement? | Yes: regex + ISO 6166 check digit (`finance/isin.py`) | A misread ISIN with a valid check digit is possible but rare |
| What kind of instrument? | Guessed from the name (`analysis.infer_asset_class`: ETF / fund / bond / structured / equity) | No reference data. A stock called "X Fund AG" is misread |
| ETF / fund ongoing cost (OCF/TER) | Yes, **only when the analyst uploads the KID** for that exact share class (`parse_kid`) | No automatic lookup. Missing KID = "unknown, not zero" (correct, but manual) |
| Fund entry/exit, transaction costs, performance fee | Read from the KID when uploaded (taxonomy L4) | Same: KID needed |
| Stock costs | Bank-side only: brokerage, custody, FX commission, Swiss stamp duty from the bank's tariff or the statement's fee lines | Stocks have no product cost (correct). FX margin (L6) and bid/ask are not estimated |
| Dividend yield | **Not covered** | Not a cost; useful context for "income vs cost" and for unreclaimed withholding tax (L9) |
| Database matching | Only the documents of the current prospect | No catalog, no cache, no external lookup |

## Sources, ranked for FeeLens

| # | Source | Gives | Access | Cost | Fit |
|---|---|---|---|---|---|
| 1 | **ESMA FIRDS** (EU instrument reference data) | Official name, CFI code (equity / fund / ETF / bond / derivative), issuer LEI, trading venues, for every instrument traded on an EU venue | Free public register and daily full/delta files (XML); no key | Free | **Use first.** CFI code replaces guessing the instrument type from its name. Tested 2026-11-25: IE00B4L5Y983 → "iShares Core MSCI World UCITS ETF", CFI CEOGES (C=fund, E=ETF) |
| 2 | **OpenFIGI** (Bloomberg) | ISIN → FIGI, name, ticker, security type, market sector, exchanges (incl. Swiss and US) | Free REST API; without key 10 ISINs per request and a low per-minute limit, free key raises it | Free | **Use second** for non-EU instruments (US stocks, Treasuries, SIX-only). Tested 2026-11-25: 30/30 test ISINs resolved |
| 3 | **Issuer KID / PRIIPs** documents | Exact share-class OCF, transaction costs, entry/exit, performance fee, cost example | Public PDF on the issuer's site (or fundinfo/Broadridge hosted) | Free | Already parsed. Next step: fetch the KID by ISIN from allowlisted issuer hosts (iShares, Vanguard, Amundi, DWS, UBS AM…), respecting robots and ToS; never UBS/BancaStato pages that block bots |
| 4 | **EMT (European MiFID Template, FinDatEx)** | Machine-readable ongoing costs, transaction costs, entry/exit, incidental costs per share class: the file banks use for their own ex-ante cost reports | Many issuers publish EMT files (CSV/XLSX) per fund; bulk via fundinfo, Broadridge, WM Datenservice | Free per issuer; bulk paid | **Best quality per figure.** A parser for EMT v4 is small (fixed field ids) and avoids PDF reading altogether |
| 5 | **fundinfo (FE fundinfo)** | KID, EMT, factsheet, prospectus for most EU/CH funds, by ISIN, with an API | Commercial licence | Typically low-to-mid five figures CHF/year | Best paid source for Swiss distribution documents. Swiss Fund Data (SFAMA) also lists CH funds but its site disallows bots: licence or manual only |
| 6 | **Morningstar Data / Direct**, **LSEG Lipper**, **Bloomberg** | Everything: OCF, TER history, dividends, classifications, holdings | Commercial | Tens of thousands CHF/year and up | Overkill for a pilot; consider when FeeLens has many users |
| 7 | **SIX Financial Information** | Swiss and global reference data, corporate actions, dividends, Valor numbers | Commercial | Quote | The Swiss standard if Safe Capital wants Valor ↔ ISIN and Swiss corporate actions |
| 8 | **EODHD / Financial Modeling Prep / Twelve Data** | Prices, dividend history and yield, some ETF fundamentals (TER) | Paid API, retail-priced | About USD 20-100/month | Good enough for dividend yield and indicative prices. TER from these is secondary: always prefer the KID for the exact share class |
| 9 | ECB / SNB reference FX rates | Daily reference FX | Free | Free | For FX-margin estimates (L6) against the rate the bank applied |
| 10 | GLEIF LEI API | Issuer legal entity from LEI | Free | Free | Links FIRDS issuer to a readable name |

Not recommended: scraping justETF, Morningstar.ch, Yahoo Finance or bank portals (ToS forbid it or bots are
blocked); unofficial wrappers such as `yfinance` (personal-use terms).

## Recommendation

1. **Now, free (story SC-6.1):** local catalog in the database, filled by FIRDS (CFI type, name) then OpenFIGI
   (anything FIRDS lacks). Cache every answer with its date and source. ISIN only, allowlisted hosts, behind
   `PCE_ALLOW_PUBLIC_LOOKUPS` and the egress guard (SC-11.5). Needs Ale's per-PR approval (external calls).
2. **Next, free (SC-6.2):** KID and EMT by ISIN from issuer sites on an allowlist; EMT parser first, KID parser
   already exists. Expected to close most "No KID for this exact share class" gaps for ETFs and large funds.
3. **Paid, when the pilot proves volume:** fundinfo licence for Swiss-distributed funds; EODHD-class API only
   if dividend yield is wanted in the report. Morningstar/LSEG only at scale.
4. Dividend yield is not a cost and must never be netted against costs in the comparison. If shown, it is
   context ("income"), with source and date.
