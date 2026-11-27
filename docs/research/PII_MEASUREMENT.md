# PII detection: what it finds and what it misses (SC-11.13 rules, SC-11.9 model)

**Update 2026-11-27 (SC-11.9).** Names, addresses and birth dates are now masked by a local model plus
rules, in `pce.pii.redact` (the one call to make before text leaves the app) and `pce.pii_names`. On the
SYNTHETIC set everything together hides 1'256 of 1'275 spans (99%) with no false flag (1'244/1'244). On
756 real public pages (KIDs, factsheets, price lists, contracts, specimen statements) it flags 0.30 names
per page, down from about 6 per page in the first test below. Details in "Name model (SC-11.9)" at the end.

**Where masking runs today.** `redact` is not called on any exit yet: the client report and the original
document download do not mask, and the public lookups send ISINs and currency codes only, never document
text. The first caller is the expert agent for hard extractions (SC-5.24), before a hosted call.

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

## Name model (SC-11.9, 2026-11-27)

**Engine.** `fastino/gliner2-privacy-filter-PII-multi` (GLiNER2-PII, Apache-2.0, mDeBERTa-v3 encoder MIT,
about 200M parameters, trained for EN/FR/DE/IT/ES/PT/NL), run by the `gliner2` package (Apache-2.0) with
its `local` extra (torch BSD-3, transformers Apache-2.0, peft Apache-2.0). No AGPL anywhere in the lock.
Optional extra `pii`; weights pinned to revision `1cb41660…` and fetched once with
`uv run python -m pce.pii_names --download`, then loaded with `HF_HUB_OFFLINE=1` and
`local_files_only=True`. The package also contains a client for the vendor's hosted API; we never build it
(it needs an API key), and a test blocks every socket while the model runs. CPU: 0.24 to 0.3 s per page.

Compared on the same set: `urchade/gliner_multi_pii-v1` (the 2026-11-13 model) does not load with
transformers 5 (needs a tokenizer that pulls `tiktoken`); `E3-JSI/gliner-multi-pii-domains-v1` same
loader. GLiNER2-PII loads with the transformers version Docling already pins, so it adds two packages
(`gliner2`, `peft`) to the lock.

**What the code adds around the model** (`pce/pii_names.py`), each measured on both sets:

| Step | Why |
|---|---|
| Labels `person`, `street_address`, `date_of_birth` only | wider labels (city, country, any date) over-mask |
| A name needs two capitalised words, no digits, no company, role or form word, one word of 3+ letters | the model reads `Person`, `Berater`, `Anleger`, `Sub-Fund`, `T T MM` as names |
| Not a name if any occurrence is followed by `AG`, `SA`, `& Co`, `(Suisse)`, `Bank`, `Funds`… | `Julius Bär & Co. AG`, `Edmond de Rothschild (Suisse) S.A.` |
| A birth date needs a birth label on its line | the model reads every date as a birth date (295 on 300 public pages) |
| Names after a holder label or a salutation are hidden even if the model missed them | lone surnames: `Gentile Signor Rezzonico` |
| Every capitalised repeat of a found name or its parts | page headers `BERNASCONI M.` |
| The postcode-and-town line under a found street | `6900 Lugano` |
| Proposals scored 0.3 to 0.5 are hidden and returned as `uncertain` | for a person to look at; a missed name is a leak, an extra mask is not |
| Rule spans always win; `redact` re-runs the rules on its output and raises if one survives | the model can only widen a mask |

**Results.**

| Kind | Rules + model |
|---|---|
| Name | 317/326 (97%) |
| Address | 190/200 (95%) |
| Birth date | 64/64 |
| Bank identifiers (6 kinds) | 685/685 |
| **All** | 1'256/1'275 (99%) |
| Precision | 1'244/1'244 (100%); fund, bank and manager names on every page stay visible |

The SYNTHETIC set now also prints fund names, the custodian and the manager on every page (Julius Bär,
Edmond de Rothschild, Safe Capital SA…): none is masked.

On 756 public pages: 228 name flags (0.30 per page) and 282 address flags. Most are company names
(`Société Générale`, `WisdomTree`), named fund managers and board members (real people, public), specimen
placeholders (`John W. Doe`, `Max Muster`) and company letterhead addresses. Hiding those loses nothing
the cost analysis needs. No ISIN, amount, rate or ordinary date is flagged.

**Still missed** (synthetic): 9 names, mostly surnames written alone in a header line with no label;
10 addresses where the street was not found, so the postcode line was not either. Same caveat as above:
the filters were tuned with these two sets in view, so real statements will do worse. An analyst checks
masked output before it leaves Safe Capital.

Re-run: `cd backend && uv sync --extra pii && uv run python -m pce.pii_names --download &&
uv run python -m tests.evaluation.pii_set`.
