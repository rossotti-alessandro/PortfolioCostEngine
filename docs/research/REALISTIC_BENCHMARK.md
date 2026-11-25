# Realistic portfolio benchmark (SC-9.8)

Date: 2026-11-25. App code: `main` at `0a74c91` vs branch `claude/project-thread-12ht53`. Lab harness, cloud
container (4 CPU, RapidOCR). Run it with `cd backend && uv run python -m pce.evaluation.realistic --n 18`
(writes `artifacts/realistic/<ts>/report.md`). End to end: `uv run python -m pce.evaluation.realistic.e2e <dir>`.

## What is tested

- **18 SYNTHETIC statements** in 6 layout archetypes: Swiss private bank (EN), cantonal bank (DE), Ticino
  bank (IT), Romandy bank (FR), Italian bank (EUR, `1.234,56`), US-style broker (USD, ISIN printed under the
  name). Fictitious banks and clients; every page says SYNTHETIC.
- **Real public instruments**: 20 stocks and 9 government bonds checked on OpenFIGI (ISIN only), and 108
  funds and ETFs from the specimen corpus with the issuers' real KIDs and hand-checked ongoing charges.
  Prices are illustrative.
- **Planted fake personal data**: name, address, IBAN and AHV with valid check digits, portfolio number,
  advisor phone and email (`.example` domains).
- **7 conditions**: digital PDF; 300 dpi office scan; 150 dpi fax-quality scan; phone photo (perspective,
  shadow, blur, JPEG) cleaned by `extraction/photo.py`; dark, steep, blurred photo; scan with pen marks;
  a handwritten list of holdings and fees in three handwriting fonts.

Why synthetic: banks publish no Swiss or Italian client statements and real ones are client data. Scraping
real people's portfolios is not allowed and is not done. The supervised pilot on real statements
(READINESS G2) is still the real test.

## Measures (exact, no tolerance)

| Measure | Meaning |
|---|---|
| words / figures | share of the printed words / numbers the reader got back exactly ("wording read right") |
| holdings | ISIN read with the exact market value |
| total_exact | printed total assets read exactly |
| fees / fee_codes | each printed fee read with the exact amount / and mapped to the right fee type |
| wrong_accepted | wrong values shown **without** a review flag, as % of values read: the safety number |
| pii_detected | planted identifiers the local detector masks (IBAN, AHV, account, phone, email) |
| mask_damage | ISINs or fee figures destroyed by masking |

## Results, 2026-11-25 (percent)

| Condition | Holdings main → branch | Fees main → branch | Total exact | Words / figures | Wrong unflagged main → branch | Gate (branch) |
|---|---|---|---|---|---|---|
| Digital PDF | 85.4 → **100** | 87.5 → **100** | 100 | 100 / 100 | 0 → 0 | PASS |
| Office scan 300 dpi | 85.4 → **100** | 79.2 → 87.5 | 94.4 | 98.4 / 97.0 | 0 → 0 | fees, figures |
| Phone photo | 85.4 → **100** | 79.2 → 91.7 | 100 | 97.8 / 99.1 | 0 → 0 | fees |
| Scan with pen marks | 83.8 → 98.3 | 77.1 → 89.6 | 100 | 98.1 / 97.8 | 1.4 → **0** | fees |
| Fax-quality scan 150 dpi | 66.7 → 77.5 | 15.6 → 18.8 | 55.6 | 77.8 / 85.5 | **15.0 → 0** | fails, retake |
| Dark, steep, blurred photo | 62.5 → 63.8 | 45.8 → 51.0 | 77.8 | 73.4 / 78.5 | **14.9 → 1.2** | fails, retake |
| Handwritten list | figures read 87.0 | – | – | – | – | PASS (≥80, person confirms) |

PII (branch): structured identifiers 100% masked on digital, 86-92% on scans and photos (OCR garbles some
emails). **Names and addresses are not masked** (72 of 72 planted): that needs the local model of SC-11.9.
Masking destroyed no ISIN and no fee figure (mask_damage 0 in every condition).

Speed: 0.6 s per digital statement, about 20 s per scanned or photographed statement (2 pages, CPU only).

### Update 2026-11-25, SC-5.23 (skewed OCR rows)

Fee lines on scans and photos lost their amount when skew put it a few points below the label. After the
fix (main after #64 -> SC-5.23): fees on office scans 87.5 -> **100%**, phone photos 91.7 -> **99.0%**,
fax-quality scans 18.8 -> 45.8%; holdings on fax-quality scans 77.5 -> 80.0%. Pen-marked scans (88.5% fees)
and dark photos (51.0%) unchanged; wrong-unflagged unchanged.

## Gates (proposed, in `pce/evaluation/realistic/__main__.py`)

| Condition | words | figures | holdings | fees | wrong unflagged |
|---|---|---|---|---|---|
| digital | ≥99.5 | ≥99.5 | ≥99 | ≥98 | ≤0.5 |
| scan, photo, annotated | ≥97-98 | ≥97-98 | ≥95-97 | ≥95 | ≤1 |
| poor scan, hard photo | ≥93-95 | ≥93-95 | ≥85-90 | ≥85-90 | ≤1 |
| handwriting | – | ≥80 | – | – | person confirms every figure |

The non-negotiable gate is **wrong unflagged ≤ 1%** in every condition: a bad picture may lower recall,
but it must never produce confident wrong numbers. The branch meets it everywhere except the dark photo
(1.2%, fee lines). Ale's 98-99% target is met on digital PDFs and, for holdings, on normal scans and photos.

## What the benchmark found and fixed (branch)

1. Broker layout with the ISIN under the name: 0 holdings read → all.
2. French "Valeur CHF" header and "Monnaie de référence": totals and currency lost → read.
3. Fee words not mapped: Fremde Spesen, Commission de change, Currency conversion fee, Exchange and
   regulatory fees.
4. PII: "Dossier titoli n." numbers not masked.
5. **Funds with share-like names** (Comgest Monde C, Sycomore Sélection Responsable) were treated as
   equities, so their uploaded KIDs were ignored and the cost reported complete: about CHF 7,800 a year
   missing on a CHF 1.7m test portfolio. A KID for the held ISIN now makes it a fund.
6. **KID performance fee**: "15% above the index" was counted as 15% of the fund's value (CHF 22,500 a
   year on one holding). The same misreading hit 8 of 130 real specimen KIDs (switching fees, entry-charge
   footnotes, a 30% benchmark weight). Now only the fee's own row counts, a rate above 5% is a share of
   outperformance and the KID's cost impact on its 10,000 example is used, else unknown.
7. **OCR drops decimal points** on poor pictures ("79'897.04" → "7989704"), and these were accepted.
   OCR-read holdings that do not add up to the printed total now all go to review.

## End to end, one prospect from a phone photo

Ticino-style statement photographed (15 holdings, CHF 1,683,582) plus the issuers' real KIDs for its 7
funds/ETFs, through the app's `extract()`, `analyse()` and the client report (EN and IT):

- All 15 holdings and the total read exactly; positions reconcile with the printed total.
- All 6 bank fees exact (advisory, custody, brokerage, FX, stamp duty, VAT): CHF 10,357.68.
- Fund ongoing charges CHF 10,089.69 vs hand-checked CHF 10,089.68 (rounding per line), plus fund
  transaction costs CHF 425.36 and a performance fee CHF 75.
- **All-in known cost CHF 20,947.72 a year = 1.24%.** Entry charges are shown as maximums, not counted.

## Not covered yet

Dividend yield (not a cost); FX margin and bid/ask spreads (L6) are listed but not estimated; ISIN type
lookup (FIRDS/OpenFIGI) and automatic KID/EMT retrieval are planned (see `INSTRUMENT_DATA_SOURCES.md`);
fee lines on pen-marked scans still miss about 1 in 9; the app should ask for a retake when a picture is too poor.
