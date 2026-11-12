# Accuracy evaluation protocol

How FeeLens proves that the numbers it shows are right, and how any extraction strategy (rule parsers,
layout models, OCR engines, local VLMs, routing, agents) is compared with the others. One scorer, one
matching rule, one set of gates. Code: `backend/src/pce/evaluation/`. Story: SC-9.1.

The product principle sets the bar: **no source, no verified figure; missing is never zero; no double
counting**. So the protocol measures more than "how many values were read": it measures how often a
number is confidently wrong, whether the cited source really shows it, whether the portfolio total is
right, and whether a wrong total is caught by a validation check before an analyst trusts it.

## Run it

```bash
cd backend
uv run python -m pce.evaluation                                   # synthetic, baseline + sabotaged (~1 min)
uv run python -m pce.evaluation --variant digital,scan            # also the image-only copies (OCR path)
python3 ../data/specimens/tools/fetch.py                          # once: public PDFs into var/specimens
uv run python -m pce.evaluation --corpus ocrbench,specimen_corpus --strategy baseline
uv run python -m pce.evaluation --strategy baseline,mypkg.mod:fn  # a new strategy, side by side
```

Output: `artifacts/eval/<UTC timestamp>/report.md` (summary table, then every error with the wanted and
the obtained value) and `results.json` (per document). Both are git-ignored because they quote public
third-party documents. Exit code 1 when the `baseline` strategy (or any listed in `--gate`) fails a gate.
The integration test `backend/tests/evaluation/test_protocol.py` runs the same protocol in the gate.

## The stages

Each stage is scored on its own, so a wrong total is attributed to the stage that caused it.

| # | Stage | Question | Metric |
|---|---|---|---|
| 1 | Classification | Is the document the type we think? | `classification_accuracy` |
| 2 | Field extraction | Did we read each labelled value, with the right number? | precision, recall, F1, `wrong_value`, `missing_as_zero`, `value_recall` |
| 3 | Location | Does the fact's box sit on the labelled value? | `bbox_hit_rate` (when the gold has value boxes) |
| 4 | Provenance | Does the cited page box / sheet cell really show that number? | `provenance` counts: verified, mismatch, no_evidence, unverifiable |
| 5 | Portfolio computation | Are AUM, known costs, comparison and saving right? | `portfolio_mismatches`, raised requests, rejected tariffs |
| 6 | Invariants | Do the money rules hold on the ledger? | `invariant_failures` |
| 7 | Detectability | When a total is wrong, did any validation check raise an alarm? | `silent_error` |
| 8 | Review load and speed | How much goes to an analyst, how long per page? | `needs_review_share`, `median_seconds_per_page` |
| 9 | End-to-end UI | Can an analyst click a number and reach its source? | Playwright suite with screenshots |

### Stage 2: the matching rule

One-to-one, greedy, value-equal candidates first, per document and page. A predicted fact matches a gold
item when, on the same page (when both give one):

1. the gold item names a fact key (`fee:CUSTODY_FEE`, `position:ZZGEQLDRA013`) and the fact has it, or
2. both carry a fee code and the codes are equal, or
3. at least half of the gold label's words (lowercase, accents stripped, 3+ letters) appear in the fact's
   label plus evidence snippet.

Values are compared as `Decimal` after normalising the printed form (`1'234.50`, `1.234,50`, `1,08 %`,
narrow no-break spaces). No tolerance: a fee that is off by a cent is wrong. A plain space is not a
thousands separator (table cells are space-separated).

| Outcome | Meaning |
|---|---|
| `correct` | matched, same value (or gold "unknown" and the fact has no value) |
| `wrong_value` | matched, different value: **the dangerous error**, a confident wrong number |
| `missing_as_zero` | a `wrong_value` where the fact says 0 and the truth is non-zero or unknown |
| `missed` | nothing matched: the analyst sees a gap, which is honest |

Precision is defined only when the gold list is exhaustive for the kinds in scope (synthetic prospects:
every value-bearing fact; benchmark pages: every fee figure on the page). The manifest `expected`
columns hold a few values a person read, so they give recall only.

### Stage 4: provenance

Independent of the extractor: the scorer opens the file, crops the cited box from the PDF text layer
(rotated watermark text removed, as the extractor does) or reads the cited spreadsheet cell, and checks
that the number is there. Image-only pages cannot be checked this way and count as `unverifiable`, never
as verified. A strategy that invents coordinates fails here.

### Stage 5 to 7: portfolio, invariants, detectability

The extracted facts of a whole prospect go through `pce.analysis.analyse` exactly as in the app. The
result is compared with numbers pinned by hand (P-1042: known cost CHF 61,449.60, saving 6,520.10;
P-2077: comparable cost 25,264.35, saving -2,588.07). The missing-document requests and the rejected
Luxembourg tariff are part of the expectation.

Invariants on any analysis, labelled or not:

- `total_known = billed + embedded + one-off`, and equals the sum of the counted lines (no double count;
  a fund's management fee inside its ongoing charge is `included_in_parent`, never counted twice);
- an `unknown` line has no amount (missing never becomes a number);
- `illustrative` and `maximum` amounts are never counted as paid;
- every counted line cites at least one source fact (traceable).

Detectability: when a total is wrong, at least one check (reconciliation, contract vs observed,
product cost reconciliation) must fail or warn. A wrong total with no alarm is a `silent_error`.

## Corpora and variants

| Corpus | Documents | Labels | Precision |
|---|---|---|---|
| `synthetic-p1042` | 11 SYNTHETIC docs, 2 banks, CHF, one scanned statement, an xlsx | built from `demo/spec.py` (the generator's inputs, never parser output) + pinned totals | yes |
| `synthetic-p2077` | 4 SYNTHETIC docs, Italian bank (EUR) and US broker (USD) | from `demo/archetypes.py` + pinned totals | yes |
| `ocrbench` | 54 pages of real public PDFs (KIDs, price lists, cost reports, statements), 4 languages | 813 hand-checked fee figures, each tagged table / key-value / text / footnote with value boxes (`data/specimens/ocrbench/groundtruth.json`) | yes, fee facts on those pages |
| `specimen_corpus` | manifest rows with an `expected` column | a few values read by a person | no |

Variant `scan` rasterises every PDF to an image-only copy at 150 dpi, so the same labels test the OCR
path. Real client documents never enter any corpus (`.claude/rules/privacy.md`).

Ground-truth labelling for the full 395-file corpus is the corpus thread's quality plan (who labels and
whether an external model may draft labels on public documents are open decisions for Ale). New labels
plug in as `GoldDoc` lists without changing the scorer.

## Gates

A strategy may become the default extractor only when, on both synthetic corpora (digital):

| Metric | Bound |
|---|---|
| classification accuracy | 100% |
| recall, precision | >= 98% |
| `wrong_value_rate` | <= 1% |
| `missing_as_zero` | 0 |
| provenance mismatches | 0 |
| portfolio mismatches, invariant failures | 0 |
| silent error | none |

and, on `ocrbench`, its recall is not lower than the current baseline's while its `wrong_value_rate` is
not higher. The sanity check runs every time: the `sabotaged` strategy (baseline with every other value
x10 and unknowns turned into 0) must fail the gates; if it ever passes, the scorer is broken.

## Adding a strategy

A strategy is a function `(filename: str, data: bytes) -> pce.evaluation.strategies.Prediction`
(document type, facts in the `Fact` shape with page + bbox or sheet + cell, profile, needs_review, page
count). Pass it as `--strategy package.module:function`. It is scored exactly like the baseline.

## End-to-end UI (stage 9)

`frontend/tests/e2e/*.spec.ts` (Playwright) drive the app on the SYNTHETIC prospects through upload,
review, costs, compare and report, and save screenshots to `artifacts/e2e/screens/`. The trace flow
(click the known total, open a fund line, see the formula, both inputs and the highlighted source box,
breadcrumbs back) is added by the "Trace numbers back to source documents" work. Before a release a
person opens the screenshots and checks that every visible number has a source and that SYNTHETIC
data says so.

## Change loop for an extraction change

1. Run the protocol on `main` and on the branch (same corpora and variants).
2. Paste both summary tables in the PR. Any new `wrong_value`, provenance mismatch or silent error
   needs a written reason or a fix.
3. The gate (`./scripts/local-gate.sh`) runs the synthetic protocol test; it must pass.

## Baseline results (2026-11-11, extractor on `main`)

| Corpus | Variant | Recall | Precision | Wrong values | Provenance mismatches | Portfolio |
|---|---|---|---|---|---|---|
| synthetic-p1042 | digital | 100% | 100% | 0 | 0 | all 9 numbers right, gate PASS |
| synthetic-p2077 | digital | 100% | 100% | 0 | 0 | all 4 numbers right, gate PASS |
| synthetic-p1042 | scan | 85.5% | 100% | 0 | (unverifiable) | 7 numbers wrong, alarms raised |
| synthetic-p2077 | scan | 96.2% | 100% | 0 | (unverifiable) | 3 numbers wrong, alarms raised |
| ocrbench (813 real fee figures, 54 pages; re-run 2026-11-12 after SC-5.7 grew the gold) | digital | 3.6% | 43.9% | 11 (27.5% of matched), 3 as zero | 8 | – |
| specimen_corpus (partial labels) | digital | 91.2% | – | 0 | 1 of 294 | – |
| sanity: sabotaged, p1042 | digital | 56.5% | 56.5% | 27 | 26 | 9 wrong, gate FAIL as intended |

What this says:

- The synthetic prospects are a regression floor, not proof of accuracy: the pipeline was written
  against them.
- On image-only copies OCR drops a CHF 600,000 position and a whole KID, so the known cost falls by
  CHF 5,700 and the saving looks bigger (10,412 instead of 6,520). The reconciliation checks fire, so it
  is not silent, but it shows why scans need their own gate before OCR results feed a client figure.
- On real public documents the production parsers find few of the hand-checked fee figures (4.3%), and
  a fifth of what they do match carries the wrong number (insurance KIDs read 0.0 where 1.9% is printed).
  This is the gap the extraction-strategy work closes; any new strategy is measured on this row.
- Provenance: on one real price list (Vontobel EAM) tiered rates cite the tier label's box, not the rate's
  box, so clicking the number would highlight the wrong text. Reported for a parser story.
