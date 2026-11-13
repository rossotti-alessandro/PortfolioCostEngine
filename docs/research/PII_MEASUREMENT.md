# PII detection: what it finds and what it misses (SC-11.9, 2026-11-13)

Question from Ale: are we masking personal data accurately and completely? Short answer: the rules
(`pce.pii`, no model) now hide every bank identifier on the test set. Names, addresses and birth dates
need a model; a local one plus "hide every repeat" reached 98 to 100% on the same set. That model is not
in the app yet: adding it is a dependency and licence decision (rule 9).

Masking is only needed where data leaves the app (an export or an outside service). The pilot sends
nothing out (ADR 0004, READINESS G8), so the pilot does not depend on these numbers.

## Test set

`backend/tests/evaluation/pii_set.py`: 100 SYNTHETIC pages (25 each in IT, DE, FR, EN) shaped like
statement text from pdfplumber or OCR. 1'275 gold spans with exact offsets. Hard cases on purpose: joint
holders, surname alone in a salutation, `SURNAME J.` page headers, the account number repeated without its
label, IBANs wrapped onto a second line or with one OCR letter/digit swap, Swiss national phone numbers
without a label. Things that must stay visible: ISINs, valor numbers, amounts, dates, fee rates, the
bank's BIC. Re-run: `cd backend && uv run python -m tests.evaluation.pii_set`.

A span counts as hidden only if every character is covered. Precision counts a flag as right when it
touches a gold span.

**Caveat.** The rule fixes were made after looking at this set, so 100% here is an upper bound. Real
statements will have layouts the set does not. The pilot should spot-check exports by hand.

## Results

| Kind | Rules before | Rules now | Local model alone | Rules + model + repeats |
|---|---|---|---|---|
| IBAN | 80/115 (70%) | 115/115 | 0 | 115/115 |
| AHV number | 57/57 | 57/57 | 0 | 57/57 |
| Payment card | 58/58 | 58/58 | 0 | 58/58 |
| Account / portfolio number | 77/200 (38%) | 200/200 | 0 | 200/200 |
| Phone | 127/155 (82%) | 155/155 | 0 | 155/155 |
| Email | 100/100 | 100/100 | 0 | 100/100 |
| Name | 0/326 | 0/326 | 222/326 (68%) | 319/326 (98%) |
| Address | 0/200 | 0/200 | 198/200 (99%) | 200/200 |
| Birth date | 0/64 | 0/64 | 64/64 | 64/64 |
| **All** | 499/1275 (39%) | 685/1275 (54%) | | 1266/1273 (99%)* |
| Precision | 100% | 100% | 75% | 96% |

\* Measured before a small change to the generator moved the total from 1'273 to 1'275 spans.

- **Rules now** (`pce/pii.py`): IBAN wrapped to the next line; after the label "IBAN", a number that fails
  the check digit is still hidden (an OCR misread, not a random number); account numbers with a country
  prefix (`CH-12345678`); Swiss national phones without a label (`091 123 45 67`); every repeat of a
  found identifier (headers repeat the account number without its label). Rows of years that pass the
  Luhn check are no longer flagged as cards (seen on a public ETF factsheet).
- **Model**: `urchade/gliner_multi_pii-v1` (GLiNER, multilingual, Apache-2.0), CPU, about 0.25 s per
  page, labels person / full name / surname / name / street address / postal code and city / date of
  birth, threshold 0.25. Alone it misses capitalised headers and lone surnames; hiding every repeat of a
  found name (case-insensitive, with a trailing initial) fixes most of that. The 7 names still missed are
  surnames the model never found anywhere on the page.
- Model false flags on the set are the bank's own address (not personal data; hiding it is harmless).

## False flags on real public documents

414 public PDFs from the corpus (KIDs, factsheets, price lists, specimen statements, contracts), first 3
pages each, 1'191 pages. These hold almost no client data, so nearly every flag is a company contact.

- Rules: 337 emails and 392 phones flagged, almost all company contact lines (`info@…`, `Tel. +41 …`);
  hiding those is harmless. Real misfires: a few long reference numbers read as phones (`#999999999999`,
  a company register number). The rule changes added 6 phones, 2 IBANs (placeholder `IBAN CHXX XXXX …` in
  forms), 1 account and 2 cards (the year row, now fixed).
- Model (same settings, first page of each of the 414 files, whole page text): 2'507 "names", 232
  addresses, 19 birth dates, about 6 names per page, on documents with almost no client data. Most are
  company names (`UOB Kay Hian`, `Edward Jones`), pronouns and form labels (`Sie`, `you`, `Nome e
  cognome`, `manufacturer`), specimen placeholders (`JOHN SMITH`, `Musterstraße 9`) and dates read as
  birth dates. 2.1 s per full page on this CPU. With "hide every repeat" a false `Sie` would hide every
  `Sie` on the page. So the model is **not usable as is**: it needs the narrower labels only (person,
  street address), a higher threshold, a stop-list of pronouns and form words, and no repeat step for
  words under 4 letters. That tuning, measured on both sets at once, is the next step of SC-11.9.

## What this means

1. Bank identifiers: covered by rules today, deterministic, no model.
2. Names, addresses, birth dates: need the model (SC-11.9 step 1), tuned first: high recall on the
   synthetic set came with heavy over-masking on real documents. Plan: an optional extra, run only at
   exits, followed by the repeat step and a leak check. A licence and dependency PR needs Ale's approval.
3. Before any export leaves Safe Capital: an analyst looks at the masked output (four-eyes), because no
   detector is complete.
