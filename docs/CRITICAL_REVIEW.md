# Critical review of the ChatGPT handoff kit

Reviewed 2026-11-06 against primary sources found on the web. Inputs reviewed: `SafeCapital_ClaudeCode_Full_Handoff.zip` (kit: docs, CSVs, `fee_engine.py`, prior-context PDFs and zips), `MASTER_PROMPT_INCOLLA_IN_CLAUDE_CODE.txt`, `Elenco_Fondi_ISIN.xlsx`. Sources are listed in [`research/SOURCE_REGISTER.md`](research/SOURCE_REGISTER.md).

## Verdict

The kit is a **good skeleton with the right instincts**: it insists that unknown costs are never zero, that a fund's management fee sits inside its ongoing charges, that a Luxembourg tariff is not a Swiss one, and that raw client PDFs must not go to an outside AI by default. We keep those rules.

It is **weak where it matters for Safe Capital's pitch**. It frames cost reporting on EU MiFID rules instead of Swiss FinSA practice, treats public price lists as if they tell us what a private-bank client pays, recommends an AGPL library for a commercial product, does not model the insurance-wrapper and Italian-client cases that the provided ISIN list itself points to, and contains several "verified" claims that it could not actually verify. Its ISIN workbook is a product catalogue, not client data. None of this blocks the project; all of it is fixed in the new research docs.

## How to read the table

Severity: **High** = would produce a wrong number or a legal/commercial risk in front of a client. **Medium** = would mislead the build or waste effort. **Low** = cleanliness. Status: **Fixed** = addressed in this PR's docs; **Open** = needs a person or a later thread.

## Findings

### Scope and framing

| # | Sev. | Finding | Evidence | Consequence | Correction | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-01 | High | The kit models the "annual ex-post cost report" on EU MiFID II/ESMA. In Switzerland, detailed accountability on costs under FinSA is largely **on request**, so many prospects will not have such a report | Kit `RESEARCH_FINDINGS.md` §8 cites ESMA only; FinSA Art. 16 (to verify on Fedlex); BDO on FINMA conduct circular (`SRC-BDO-FINMA-RS`) | Tool assumes a document most Swiss prospects don't hold; results look incomplete | Planner asks for it; product generates a ready-to-sign request letter to the bank for costs **and** retrocessions (`research/DOCUMENT_TAXONOMY.md` §3) | Research | Fixed (design); article text Open |
| F-02 | High | The pitch output ("you would pay less with Safe Capital") is comparative advertising, but the kit treats it only as a privacy/compliance topic | Kit `COMPLIANCE_REVIEW.md`; UWG Art. 3(1)(e) on comparisons (to verify with counsel) | A misleading saving claim is a legal and reputational risk | Default comparison = same holdings, both sides at "estimated all-in" with coverage shown; one-off switching costs separate; compliance sign-off on report template (`research/SAFE_CAPITAL_PROFILE.md`) | Compliance (Safe Capital) | Open |
| F-03 | High | Safe Capital is an external asset manager, so its proposal = its fee **plus a custodian's fees plus product costs**. The kit's comparison inputs focus on a "Safe Capital tariff" | Safe Capital site (`SRC-SC-WEB`): 50+ custodian partners | Comparing bank all-in vs Safe Capital fee alone would overstate savings | Proposal scenario requires a custodian tariff input (`proposal_custodian_tariff` in `document_types.csv`) | App thread | Fixed (taxonomy) |
| F-04 | Medium | Brand ambiguity: kit alternates "3MC", "Safe Capital", "Safe Capital / 3MC". "3MC" does not appear on Safe Capital's site | Kit README; `SRC-SC-WEB` | Wrong name on a client report | Ask Massimo; product is generic and multi-tenant (Ale asked for a tool "usable by anyone") | Ale / Massimo | Open |
| F-05 | Medium | Safe Capital's FINMA licence is stated by its site ("authorized by FINMA and Supervised by OSIF") but neither the kit nor this pass could confirm it in the FINMA list (the "S" pages were unreadable to our tools) | `SRC-FINMA-VVTR` partial | Quoting an unverified licence in a deck | Five-minute manual check of FINMA XLSX and OSIF list before the deck goes out | Ale | Open |
| F-06 | Medium | Master prompt asks for a production-grade platform in one go (LangGraph, OpenTelemetry, KMS, RLS, VLM benchmarks, multi-agent claims) | `MASTER_PROMPT…txt` §2–§4 | Demo delayed by infrastructure that adds no client value yet | Phase it: demo on synthetic data with local extraction first; harden for real data after Massimo validates | Coordinator / backlog thread | Open |

### Data provided

| # | Sev. | Finding | Evidence | Consequence | Correction | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-07 | High | `Elenco_Fondi_ISIN.xlsx` (386 ISIN classes, snapshot 27 Oct 2026) has **no quantities, values or fee figures**; 231 of 386 ISINs (60%) come from one Italian unit-linked insurance contract (Mediolanum Vita "My Life Special", Feb 2025) | Workbook sheets PANORAMICA, FONTI; kit's own audit PDF agrees ("0 fee numeriche") | Cannot be used as client data or as a cost source | Use only as seed for an instrument catalogue and as a test list for KID retrieval | App thread | Fixed (documented) |
| F-08 | Medium | That skew is a signal the kit ignored: Lugano prospects often hold **Italian insurance wrappers** and Italian bank documents | Same; Safe Capital manages for life insurers (`SRC-SC-WEB`) | Wrapper costs (admin, risk, surrender) missed; Italian formats unsupported | Wrapper layer L7 in fee taxonomy; Italian labels and `1.234,56` number format in document taxonomy | Research | Fixed |
| F-09 | Low | The kit's fictitious bank statements are internally consistent (e.g. Bank Alfa positions sum to CHF 1'500'000; bond 700'000 × 98.50% = 689'500) and clearly labelled "SIMULAZIONE DIDATTICA" | `3MC_Estratti_Bancari_Fittizi_Prospect.pdf` | Good as a first test fixture | Keep as synthetic gold set; never present as real | App thread | Fixed |

### Fee methodology

| # | Sev. | Finding | Evidence | Consequence | Correction | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-10 | High | No status for **public list price**. Kit lets a published tariff produce an "estimated" cost like a KID does. Private banks (UBS, Julius Baer CH, LGT) do not even publish mandate prices; clients negotiate | UBS Manage/Advice pages show no prices (`SRC-UBS-WEB`); BancaStato mandate rate not published (`SRC-BS-MANDATE`); only JB **Luxembourg** tariff is public (`SRC-JB-LUX`) | Estimates presented with false confidence | New status `PUBLIC_TARIFF` (weak), separate from `CONTRACTUAL` (client's own tariff) | Research | Fixed |
| F-11 | High | Fund transaction costs and performance fees are **outside** TER/OCF. Kit gets this partly right but its taxonomy names the total `OCF_TOTAL`, inviting the reading that OCF is the total product cost | PRIIPs Delegated Reg. 2017/653 Art. 5: one-off, recurring (transaction; other), incidental listed separately (`SRC-PRIIPS-653`) | Under-estimate of fund costs | `FUND_ONGOING` + `FUND_TRANSACTION` + `FUND_PERFORMANCE` as siblings; `FUND_MGMT_FEE` child of ongoing | Research | Fixed |
| F-12 | High | Structured products: kit says issuer margin is "often unknown". The Swiss industry guideline defines entry cost = **price minus fair value** and asks issuers to publish daily cost data free on a website | SSPA cost guideline 2019 (`SRC-SSPA-COST`) | Large embedded cost left as unknown when it is often obtainable | `SP_ENTRY_COST` sourced from issuer KID/cost data; amortise over term in the annual view | Research | Fixed |
| F-13 | Medium | Swiss VAT on fees depends on client domicile (generally no Swiss VAT for clients domiciled abroad, to verify). Kit only says "client-dependent" with no field to drive it | Swissquote: "VAT of 8.1% is applied to custody fees" (`SRC-SQ-FEES`); JB and BancaStato quote prices ex VAT | Italian-resident client vs Swiss-resident client compared wrongly | Client domicile captured at step 1; fees stored net with VAT separate | App thread | Fixed (design) |
| F-14 | Medium | Retrocessions mixed into the cost list as `THIRD_PARTY_REBATE`. They are not an extra cost (already inside product costs); only refunds to the client are credits | Kit `fee_taxonomy.csv`; FINMA conduct expectations via BDO (`SRC-BDO-FINMA-RS`) | Double counting or wrong netting | Side ledger `RETRO_RECEIVED` (info, never summed) + credit `RETRO_REFUNDED` | Research | Fixed |
| F-15 | Medium | Swiss stamp duty treated as a comparison cost. It is a tax, identical at any Swiss bank for the same trades | Kit `fee_taxonomy.csv` `SWISS_STAMP` | Inflates "bank cost" side | Shown, but excluded from the provider comparison by default | Research | Fixed |
| F-16 | Medium | All-in mandates are common in Ticino (BancaStato: flat quarterly fee "includes brokerage, management and custody") but kit has no `ALL_IN_FEE` parent | `SRC-BS-MANDATE` | Custody and brokerage added on top of an all-in fee | `ALL_IN_FEE` parent with explicit exclusion list | Research | Fixed |

### Kit code (`backend/fee_engine.py`, read only; not executed)

| # | Sev. | Finding | Evidence | Consequence | Correction | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-17 | High | `sum_costs` raises an error if any atom is `UNKNOWN`. With real documents there is almost always an unknown (FX margin), so no total can ever be shown | `fee_engine.py` lines 76–77 | Dashboard cannot render | Return proven total, estimated total and an unknown list with coverage, not an exception | App thread | Open |
| F-18 | Medium | `bps_fee` applies the minimum once per year. Tariffs set minimums per quarter (JB Lux: EUR 360/quarter) | `fee_engine.py` lines 21–26; `SRC-JB-LUX` | Small portfolios under-estimated | Compute per billing period, then annualise | App thread | Open |
| F-19 | Medium | `money_roundtrip` "optimized" scenario drops the CHF 10'200 embedded product costs and replaces them with CHF 3'000 without stating which products | `fee_engine.py` lines 100–108 | A demo saving that cannot be explained | Optimised scenario must list proposed ISINs and their KIDs | App thread | Open |
| F-20 | Low | `economic_group` must be unique across atoms, so two accounts each with a custody fee need artificial group names | lines 84–86 | Brittle | Key by (group, account, period) | App thread | Open |

### Sources and tooling

| # | Sev. | Finding | Evidence | Consequence | Correction | Owner | Status |
|---|---|---|---|---|---|---|---|
| F-21 | High | Kit recommends **PyMuPDF**, which is AGPL-3.0 (commercial licence from Artifex otherwise) | PyPI `SRC-PYMUPDF` | Licence breach if shipped in a closed or hosted product | Use pdfplumber + Docling + pypdfium2 (permissive) (`research/EXTRACTION_TOOLING.md`) | App thread | Fixed (recommendation) |
| F-22 | Medium | Kit plans automated KID retrieval from swissfunddata.ch. Its terms forbid professional data vendors to systematically extract, scrape or commercially exploit the data without SIX consent | `SRC-SFD` | Licence risk for a commercial tool | Analyst-triggered single downloads, issuer sites, or a licensed feed (SIX/fundinfo/FinDatEx EMT) | App thread / Safe Capital | Open |
| F-23 | Medium | ISIN lookups via OpenFIGI or any external API leak the prospect's holdings to a third party | `SRC-OPENFIGI` | Privacy | Local catalogue first; never send quantities; consider decoys or batching | App thread | Fixed (design) |
| F-24 | Medium | Some kit "official examples" are irrelevant to Swiss prospects: UBS **US** holdings and review samples from 2014 | Kit `official_sources.csv` UBS-HOLDINGS, UBS-REVIEW | Wrong layouts used as reference | Keep only as generic layout examples; get real anonymised Swiss samples from Massimo | Massimo | Open |
| F-25 | Low | Kit `field_dictionary.csv` repeats identical "why" and "validation" text on every row of an entity | `data/field_dictionary.csv` | Looks complete but adds no rules | App thread defines field-level validation from the new taxonomies | App thread | Open |
| F-26 | Low | Kit marks several sources "verified" where its own notes say screenshots failed | Kit `RESEARCH_FINDINGS.md` gap section | Overstated evidence | New register uses read / partial / listed / failed / kit-only | Research | Fixed |
| F-27 | Low | Kit cites Swiss law only through ESMA and FDPIC pages, no statute text. We also could not render Fedlex (JavaScript only) | `SRC-FINSA`, `SRC-FADP` failed | Article numbers unconfirmed | Open verification list in source register | Ale / counsel | Open |

## What we keep from the kit

The non-negotiable rules (unknown ≠ zero, no AMF+OCF double count, KID illustration ≠ actual, Luxembourg ≠ Swiss, local-first privacy), the three-view idea (cash billed, economic, forward comparable), the missing-data alert contract, the evidence model (document, page, bounding box, snippet), and the fictitious statements as test fixtures.

## New research documents in this PR

- [`research/FEE_TAXONOMY.md`](research/FEE_TAXONOMY.md) and [`../data/taxonomy/fee_taxonomy.csv`](../data/taxonomy/fee_taxonomy.csv): 10 layers, 44 codes (incl. credits and the retrocession side ledger), evidence statuses, double-count rules.
- [`research/DOCUMENT_TAXONOMY.md`](research/DOCUMENT_TAXONOMY.md) and [`../data/taxonomy/document_types.csv`](../data/taxonomy/document_types.csv): 31 document types with IT/DE labels, priorities, what each proves.
- [`research/SOURCE_REGISTER.md`](research/SOURCE_REGISTER.md): every source with honest status.
- [`research/SAFE_CAPITAL_PROFILE.md`](research/SAFE_CAPITAL_PROFILE.md): who the client is, questions for Massimo.
- [`research/DATA_PRIVACY_AND_HOSTING.md`](research/DATA_PRIVACY_AND_HOSTING.md): where it should run and why.
- [`research/EXTRACTION_TOOLING.md`](research/EXTRACTION_TOOLING.md): OCR/extraction libraries with licences.
- [`research/UX_RECOMMENDATIONS.md`](research/UX_RECOMMENDATIONS.md): screens and dashboard elements that follow from the research.
