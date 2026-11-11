# Extraction strategy: how FeeLens finds and reads every fee (SC-5.8)

Status: measured 2026-11-11 on the SC-5.6 hand-checked benchmark. Decision input for ADR 0003; this
document does not change the ADR by itself. Numbers below come from `data/specimens/strategies/run.py`
(results table: [`data/specimens/strategies/RESULTS.md`](../../data/specimens/strategies/RESULTS.md)).

## Decision in one paragraph

Read every page deterministically (text layer, OCR only where there is none), find every rate and
amount, and link each one to its label with **page geometry**: the row label (grown over wrapped
lines), the column header and the section path above. Then **verify** each value: a second,
independent reading of the printed pixels at the value's box, a second linker (the per-type parser)
at the same spot, and arithmetic and plausibility checks. Doubtful values are flagged
`needs_review` with a reason and stay visible; nothing is dropped, corrected or invented, and values
the type parsers did not produce (`fee_mention`) never enter a total until an analyst accepts them.
No RAG and no LLM in the number path. Layout models and VLMs stay optional fallbacks: on this
benchmark they add little for born-digital pages and cost 4 to 200 times more time.

## What was measured

- 44 benchmark pages (36 real public pages from 18 document families in EN/DE/FR/IT, 2 true scans,
  6 simulated scans), 572 hand-checked fee figures (514 distinct; scan copies reuse their original's
  gold). Ground truth: `data/specimens/ocrbench/groundtruth.json`, read from the rendered page.
- Matching rules agreed with the accuracy-protocol thread (SC-9): one-to-one per page; value equal as
  a Decimal; label matches when at least half of the gold label's words appear in the predicted label
  and evidence snippet.
- **Wrong values** = predictions whose label matches a printed fee on the page but whose value matches
  none, plus unmatched zeros (missing must never become zero). This is the dangerous error.
- **(accepted)** columns count only values not flagged `needs_review`: what would flow on without an
  analyst looking.
- CPU only (4 cores), median seconds per page including any stored model time.

## Results (all 44 pages)

| Strategy | Precision | Recall | F1 | Wrong values | Needs review | Wrong (accepted) | s/page |
|---|---|---|---|---|---|---|---|
| Type parsers before SC-5.8 (`rules`) | 60% | **4%** | 0.08 | 12.5% | 0% | 12.5% | 4.4 * |
| Line rule (number + fee word on one line) | 76% | 51% | 0.61 | 16.6% | 0% | 16.6% | 0.5 |
| **Finder** on the text layer | 78% | **92%** | 0.84 | 18.9% | 0% | 18.9% | **0.25** |
| Finder + Heron table regions | 78% | 92% | 0.85 | 18.9% | 0% | 18.9% | 1.0 |
| Finder + PP-DocLayoutV3 table regions | 79% | 92% | 0.85 | 19.1% | 0% | 19.1% | 1.3 |
| Finder on RapidOCR lines (all pages OCR'd) | 83% | 90% | 0.86 | 12.6% | 0% | 12.6% | 4.6 |
| Finder on Tesseract lines | 65% | 74% | 0.69 | 15.5% | 0% | 15.5% | 3.9 |
| Finder + verify (RapidOCR full page as 2nd reader) | 78% | 92% | 0.84 | 18.9% | 19% | 8.2% | 6.1 |
| **Finder + verify (Tesseract on value crops)** | 78% | 92% | 0.84 | 18.9% | 22% | **8.0%** | **1.5** |
| **App `extract()` after SC-5.8** (parsers + finder, cross-checked, verified) | 75% | 82% | 0.78 | 20.0% | 28% | 8.2% | 4.1 * |
| VLM tables anchored to text boxes: Docling | 76% | 61% | 0.67 | 13.9% | 2% | 13.8% | 4.7 |
| VLM tables anchored to text boxes: PaddleOCR-VL (23 core pages only) | 86% | 66% | 0.75 | 8.0% | 1% | 8.1% | 57 |

\* whole-document extraction time divided by its pages; the app refuses files over 200 pages (one
benchmark prospectus. The app path also keeps the parser's label when both linkers read the same value
and skips finder-only total rows on pages a parser already read (their components are there); both
were needed to keep the accuracy protocol's synthetic precision gate green and its wrong-value count on
the real pages at main's level. Together they explain the gap between the finder alone (92%) and the
app path (82%).

Accuracy protocol (`python -m pce.evaluation`, ledger kinds only, so `fee_mention` is out of scope on
ocrbench): identical to main on ocrbench (recall 4.3%, precision 43.1%, 5 wrong values) and 100% on
both synthetic portfolios, all gates PASS.

For comparison, the SC-5.6 benchmark's best model linked 69% of fees to the right row (PaddleOCR-VL
hybrid, 53 s/page) and the cheap hybrid 62% (1 s/page). The finder reaches 92% at 0.25 s/page because
the gap was never reading the digits (values are read 96%+ by every good reader) but **linking** them:
labels wrap over two to four lines, sit beside a vertically centred value, live in a column header
("Minimum", "If you exit after 1 year") or in the section title above a tier table ("Transaction fees ›
Equities and bonds › Up to CHF 25,000").

### What the remaining wrong values are

"Wrong (accepted)" is 8.0% for the verified finder. A manual audit of those 51 values against the
rendered pages:

| Cause | Share of the 51 | Example |
|---|---|---|
| Printed fees the gold file omits (gold incomplete, not an error) | about half | Passadore's repeated minimum "10,00" on every tier row; HSBC's 0.00 % ancillary and incidental rows; BCV card fees beyond the 19 labelled |
| Right value, label partly wrong | about a fifth | a KID amount labelled with the description column instead of the row label |
| Real non-fees accepted | about a quarter (≈2.5% of accepted values) | worked examples in running text ("49 751,24 € investis x 0,5 %"), a fund annual report's statement of operations |

So the true accepted wrong-value rate is near 2 to 3%, above the 1% gate the accuracy protocol
proposes. That is why finder-only values are `fee_mention` facts (shown, clickable, not in totals) and
type-parser facts keep feeding the cost engine exactly as before. The gold omissions are reported to the
model-lab thread so the file can be corrected.

## Answers to the questions asked

### Should we use RAG?

**Not for extracting numbers.** RAG retrieves passages and lets a language model compose an answer.
That breaks the two rules the product stands on: every number must point to a page and a box, and no
number may be invented or computed by a model. It is also unnecessary: client documents are small
(a statement is 5 to 40 pages; the app caps uploads at 200), and the finder reads **every** page at
0.25 s/page, so there is nothing to retrieve that a full scan does not already see. Retrieval earns its
place later in two narrow jobs: (1) analyst questions across a prospect's documents ("where is the
custody fee mentioned?"), answered with links to boxes, and (2) locating the cost section inside a
long prospectus or annual report before the finder runs. Both would run locally (ADR 0004).

### Should we search over the OCR output?

**Yes, as an analyst feature, lexical first.** Every page already yields words with boxes (text layer
or OCR), so a per-document index of words + boxes is free. Keyword search with the multilingual fee
vocabulary (`finder.FEE_WORDS`, `vocab.FEE_LABELS`) covers the need: it is what powers the "possible
misses" list (cost-looking lines with no extracted value). Embedding search adds little for four
languages of fixed financial vocabulary and is not needed now.

### Which layout elements must we identify?

Measured by what the finder needed to reach 92% recall, in order of impact:

1. **Row label blocks**, including labels wrapped over several lines and values printed beside the
   middle of a label block (KIDs, cost reports).
2. **Column headers** above each value ("Rate p.a.", "Minimum", "If you exit after 1 year", "SIX",
   "XETRA").
3. **Section path**: the nearest title above a table and the nearest fee title above that.
4. **Tier and band limits** ("bis CHF 500'000", "Next CHF 2 million") which are labels, not fees.
5. **Non-fee zones**: KID performance scenarios, worked examples, returns and volatility tables,
   annual-report P&L rows, phone numbers and addresses in footers.
6. **Descriptions vs labels**: long text cells beside a value are context, not its label.
7. **Repeated and hidden text**: ditto marks that repeat a minimum, and text layers that differ from
   the printed page (caught by the second reading, not by layout).
8. **Table vs running text**: a zero in running text is flagged, a zero in a fee table is a fact.

Table **regions** from a layout model (Heron, PP-DocLayoutV3) were tested as a scope for header search:
+0.01 F1, +0.7 to 1 s/page. Not worth it on born-digital pages today; worth keeping for scans and
for documents where geometry alone mixes two side-by-side tables.

### Should there be an agent, or routing by document and page type?

**Deterministic routing, yes; an LLM agent in the number path, no.**

- Per page: text layer when it has one (pdfplumber), OCR otherwise.
- Per document: the type parser (statement, cost report, tariff, KID, termsheet) still runs, because
  it knows semantics the finder does not (positions, ISINs, fee codes, inclusion rules).
- Every page: the finder runs too, and the two are **cross-checked** at the same spot. Agreement adds
  a passed check (the parser keeps its own label; the finder's is stored as context, because
  swapping labels made parser misreads look confident); disagreement keeps both readings, both flagged.
- An agent (local model, ADR 0004) can help later with triage, not values: suggesting the fee code for
  a `fee_mention` label, grouping review items, drafting the bank request letter for what is missing.

### How do we make sure every number is accurate?

Layered, each layer measured or tested:

1. **One Decimal reader** for every engine (`extraction/numbers.py`): Swiss, EU and US separators,
   negatives as `(3.28)`, `-3.28` or `3.28-`, `CHF 125.-`, currencies before or after, rates in % / bp.
   Dates, ISIN digits and numbers glued to words are never values. Unit-tested.
2. **Exact boxes**: a number inside a longer cell gets the box of its own words, not an estimate.
3. **A second, independent reading**: every value box is cropped from the rendered page and re-read by
   Tesseract (one call per page, table rulings removed, 400 dpi). Agreement is recorded per value;
   disagreement or nothing printed there means `needs_review`. This caught a whole page whose text
   layer differs from what is printed (BCV price list).
4. **Two linkers**: type parser and finder must agree on the value at the same place.
5. **Plausibility**: ambiguous `1.250` on a page that does not show its decimal style, zeros in
   running text, ongoing annual rates above 3 %, amounts of a million or more whose only fee word is a
   section title. All flag, none correct.
6. **Arithmetic**: a total row that equals the sum of the rows above it in its column is recorded as a
   passed check (`components_sum_to_total`).
7. **Analyst review of everything flagged**, with the alternatives shown, before it reaches a total.

On the benchmark this flags 22% of values for review and leaves 8.0% of accepted values unmatched,
of which about a third are real mistakes.

## Pipeline (what `extract()` does now)

```
PDF bytes
 ├─ read_pdf: per page, pdfplumber words+boxes, or Tesseract when there is no text layer
 ├─ classify → type parser (statement / cost report / tariff / KID / termsheet)   [unchanged]
 ├─ finder.find_fees: every rate/amount + label path + value/label/row boxes        [new]
 ├─ verify.second_reading: Tesseract re-reads each value crop from the rendered page [new]
 ├─ verify.verify: review status + reasons + checks on every finder value          [new]
 └─ cross-check: parser fact at the same spot gets the review (finder label as context);
                 finder-only values → kind "fee_mention" (not in totals)            [new]
```

Every fee value carries `evidence.page`, `bbox`, `label_bbox`, `row_bbox`, `region`, the printed
text, and `review` (also mirrored in `extra["review"]` so it is stored without a schema change).

## Not done, and why

- **Scans.** On scans the finder works as well as its reader. Tesseract lines give F1 0.69, RapidOCR
  (Apache-2.0, ONNX, CPU) 0.86. Switching the scan reader to RapidOCR is the biggest next gain; it adds
  a dependency to `backend/pyproject.toml` (a serialised path), so it is a separate story.
- **VLMs** (PaddleOCR-VL, Granite-Docling, Qwen3-VL): better than OCR on hard scans, 50 to 150 s/page
  on CPU, and their outputs carry no reliable boxes. Kept as a fallback for pages flagged unreadable.
- **Worked examples and annual reports**: the remaining real errors. Next rule: treat numbers inside
  running text with arithmetic operators or "e.g./par exemple/Beispiel" as examples.
- **Gold corrections**: about half of the residual "wrong" values are printed fees missing from the gold
  file; the list is in the PR for the model-lab thread.

## How to rerun

```bash
python3 data/specimens/tools/fetch.py                     # public PDFs -> var/specimens (not in git)
# pages + stored engine outputs: see data/specimens/ocrbench/README.md (or copy var/ocrbench/out)
cd backend && uv run python ../data/specimens/strategies/run.py            # all strategies
cd backend && uv run python ../data/specimens/strategies/run.py --only "finder @text"
```
