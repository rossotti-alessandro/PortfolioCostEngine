# Extraction and revalidation protocol (SC-5.14)

How FeeLens turns an uploaded document into figures an analyst can trust: the order of steps, what runs
in parallel, how each figure is validated, and what the agentic revalidation adds. Measured on the 63
hand-checked benchmark pages (`data/specimens/ocrbench`), scored by the workflow arena
(`data/specimens/arena/RESULTS.md`). Public documents only; no client data.

Product rule behind every step: **no source, no verified figure; missing is never zero; a doubt goes to
the analyst, never into the totals.**

## 1. Order of steps

| # | Step | Unit | Parallel? | What it produces | Code |
|---|---|---|---|---|---|
| 1 | Ingest | document | documents in parallel | hash, page count, text layer or scan per page | `api.py` upload, `layout.read_pdf` |
| 2 | Read pages | page | **yes**: process pool for OCR (PR #21: 50-page scan 84 s → 22 s on 4 cores) | words and lines with boxes (PDF points) | `layout.py` |
| 3 | Classify | document | – | document type, institution, dates | `parsers.classify` |
| 4 | Find candidates | page | yes (pure, ~0.25 s/page) | each figure linked to row label, column header, section | `finder.py` (PR #15) |
| 5 | Verify | page | yes | second reading of each value crop (Tesseract), rule checks | `verify.py` (PR #15) |
| 6 | **Revalidate** | value, page | pages yes; the model critic is one process, batched per page | confirm or flag per value, never a new number | `revalidate.py` (this story) |
| 7 | Decide | value | – | `accepted` or `needs_review` with reasons | `revalidate.decide` |
| 8 | Cost engine | prospect | – | ledger, inclusion graph (AMF inside OCF once), tariffs by jurisdiction and date | `analysis.py`, `finance/` |
| 9 | Analyst review | prospect | – | every number clickable to page and box; review queue | UI (SC-8.9, SC-8.10) |
| 10 | Report | prospect | – | client report without internal margin | `report.py` |

Steps 2, 4, 5 and 6 work page by page and pages do not depend on each other, so they can run in a pool.
On Render free (0.15 CPU, one worker) parallelism gains nothing; the language-model critic does not run
there at all.

## 2. Validation layers

| Layer | Question | How | Where |
|---|---|---|---|
| Reading | Is this the number printed here? | two independent readers read the same number at the same box (text layer vs Tesseract crop; RapidOCR, docTR, vision table row on doubt) | `verify`, `revalidate` readers |
| Field | Is the value plausible for its field? | zero only in a table, ongoing rate ≤ 3 %, separator unambiguous, no million-sized "fee" from a heading | `verify` |
| Document | Do the page's figures agree with each other? | rows add up to the printed total; KID amount on 10 000 = its % (Decimal, rounded to the printed decimals) | `revalidate.reconcile_*` |
| Meaning | Is it a fee at all? | local language model critic, flag only | `arena/revalidate_lab.py` (lab) |
| Cross-document | Does the same ISIN's cost agree across KID, factsheet, statement? | not built yet: follow-up story | – |
| Portfolio | Are the totals coherent? | inclusion graph, wrap fees replace, missing ≠ 0, tariffs by booking jurisdiction | `finance/` |
| Human | Does the analyst agree? | review queue; nothing unconfirmed enters a total | UI |

A value is **accepted** only when its reading is confirmed (two independent readers, or page arithmetic)
and no rule or critic raised a doubt. Everything else is shown, flagged, with the reasons, and stays out
of the totals until the analyst accepts it.

## 3. The revalidation graph (step 6)

```
            ┌──────── reading doubt ────────┐
 value ──▶ triage                          readers ──▶ reconcile ──▶ critic ──▶ decide ──▶ accepted
            └──── reading confirmed ──────────────────▲             (optional)        └──▶ needs_review
```

- **State**: one `Case` per value: the fact (value, label, page, box), the opinions gathered, the path taken.
- **Supervisor (`triage`)**: deterministic routing. Only values whose reading is in doubt (`engines_disagree`,
  `not_confirmed`) visit the readers; the others go straight to the page checks.
- **Specialists** return an `Opinion`: `confirm`, `flag` or `abstain` plus a short reason. They cannot
  return a number, so they cannot invent, correct or round one.
  - *readers*, cheapest first, stop at the first that reads the same number at the same box.
  - *reconcile*: arithmetic the page states (totals, KID % vs amount). Clears reading and separator doubts.
  - *critic*: a local model asked "is this a fee?". Only its flags count; it can never confirm.
- **Decision**: reading doubts are cleared only by a reader or by arithmetic; rule doubts (rate out of range,
  zero in text, implausible amount) and low OCR confidence are never cleared by a specialist; any flag
  sends the value to review. The opinions are recorded as `revalidate:<specialist>` checks, so the trace
  view shows who confirmed what.

Why not LangGraph: the graph has four nodes and one conditional edge. Plain Python keeps it readable,
testable without a model, and free of a new dependency. The concepts map one to one (state = `Case`,
nodes = functions, conditional edge = `triage`), so moving to LangGraph (MIT) later is mechanical if the
graph grows loops or human-in-the-loop interrupts.

Why the model never writes a number: the arena showed a model that may drop figures removes real fees
(175 of 899 when it could drop), and a model that writes figures cannot point to a page and box. In this
graph the model only adds doubt.

## 4. Results

All 63 pages, 899 hand-checked fees, 4 CPU cores (`data/specimens/arena/RESULTS.md`, 2026-11-12). The graph
never drops a figure, so every variant finds the same 90% of fees as finder + verify; what changes is
which figures an analyst must look at, and how many wrong ones get through without a look.

| Workflow | Fees found | Wrong values accepted | Sent to review | s/page (median) |
|---|---|---|---|---|
| Finder + verify (PR #15, today's default) | 90% | 48 (5.9%) | 18% | 1.2 |
| Revalidation: arithmetic only (app, `PCE_REVALIDATE=1`) | 90% | 48 (5.8%) | 17% | 1.2 |
| Revalidation: more readers | 90% | 54 (6.4%) | 15% | 1.2 (mean +5 s: readers run on 115 of 992 values) |
| Revalidation: readers + arithmetic | 90% | 54 (6.3%) | 14% | 1.2 (mean +5 s) |
| Revalidation: full graph (+ model critic) | 90% | 30 (4.6%) | 34% | 41.5 |
| Revalidation: full, critic ignores zeros | 90% | 32 (4.6%) | 29% | 41.5 |
| Agent flags only (SC-5.10, for reference) | 90% | 27 (4.4%) | 38% | 36.9 |
| Two readers must agree (23 pages only) | 91% | 0 (0.0%) | 62% | 58.6 |

95% intervals over pages (1000 resamples): wrong accepted 3.4–9.0% (arithmetic only), 2.0–8.1% (full graph);
review 7–28% and 24–45%. Held out (without the 3 pages the critic prompt was tuned on): wrong accepted
4.8% (arithmetic only) and 3.7% (full graph). The intervals overlap: on 63 pages the differences between
neighbouring rows are indicative, not proven.

What each specialist did:
- **Arithmetic** confirmed 9 values whose reading was in doubt (all right) and resolved separator doubts.
  It never accepted a wrong value. The accuracy protocol (`python -m pce.evaluation`, SYNTHETIC
  prospects, digital and scan) gives identical results with it on and off: all gates pass.
- **More readers** (RapidOCR, docTR, vision table row) confirmed 28 right values and 3 wrong ones (6 in
  the scorer's count, which also re-pairs neighbouring figures with the gold fees). The wrong ones were read correctly: a footnote marker glued to a figure ("CHF 100,000²" printed as
  "100,0002") and a scan where the label was linked to the wrong row. A reader can only vouch for the
  digits, not for the meaning. A first version also let readers clear low OCR confidence; that accepted
  two values with misread labels, so low confidence now always stays with the analyst.
- **The critic** (Qwen3-4B, local) is the only specialist that lowers wrong values (48 → 30) and the most
  expensive. Of the figures it sent to review, 16 were wrong values and 152 were real fees: it sends 16
  more points of figures to review and needs about 40 s per page on 4 CPU cores
  (up to 7.5 minutes on a 50-figure price list).

## 5. Recommendation

1. **Turn page arithmetic on in the app** (`PCE_REVALIDATE=1`). It is free, deterministic, never
   accepted a wrong value and fewer values wait for review. Off by default in this PR so the decision is Ale's.
2. **Do not add the extra readers on their own.** They save the analyst 3–4 points of review but let 6
   more wrong values through. Their value is inside a two-reader rule, not as a shortcut past review.
3. **Keep the model critic optional, for a local install with CPU to spare**, never on Render free.
   Compared with finder + verify it cuts wrong accepted values from 5.9% to 4.6%, keeps every fee, and
   doubles the review share (18% → 29–34%). It is the honest price of a semantic check with a 4B model.
4. **Next levers**, in order of expected gain:
   - rank the review queue with the MiniCPM-OCR-Jev misread detector (SC-5.13: 48% of misreads caught
     in the top 10% of review) so the critic's extra review costs less analyst time;
   - a faster, stronger second reader (table structure, SLANet) so "two readers must agree" (0 wrong
     accepted) no longer costs 62% review;
   - a cross-document check (same ISIN, same cost in KID, factsheet and statement) as a new story.

## 6. Running it

```bash
# app: page arithmetic on every upload (off by default)
PCE_REVALIDATE=1 uv run uvicorn pce.api:app

# lab: benchmark pages, stored lab outputs and the finder harness (see data/specimens/ocrbench/README.md)
cd backend && uv run python ../data/specimens/strategies/run.py
var/ocrbench/.venv/bin/python data/specimens/arena/agent.py --model Qwen/Qwen3-4B-Instruct-2507 --dtype bfloat16
cd backend && uv run python ../data/specimens/arena/revalidate_lab.py && uv run python ../data/specimens/arena/run.py
```

Licences: Qwen3-4B-Instruct-2507 Apache-2.0, RapidOCR Apache-2.0, docTR Apache-2.0, PaddleOCR-VL
Apache-2.0. The lab venv is separate from the backend lock file; the backend gains no dependency.
