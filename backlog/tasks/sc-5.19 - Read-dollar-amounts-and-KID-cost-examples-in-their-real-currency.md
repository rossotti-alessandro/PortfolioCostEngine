---
id: SC-5.19
title: Read "$" amounts and KID cost examples in their real currency
status: "Done"
assignee: []
owner: "Validate accuracy and speed up processing"
model: "claude-opus-5-5"
progress: 100
branch: "claude/sc-5.19-currency-misreads"
pr: ""
created_date: "2026-11-13 13:23"
updated_date: "2026-11-13 13:41"
labels:
  - extraction
dependencies: []
parent_task_id: SC-5
priority: P1
paths_owned:
  - "backend/src/pce/extraction/parsers.py"
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_currency_misreads.py"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs: [".claude/rules/extraction.md", ".claude/rules/finance.md"]
---

> **One-liner**: A "$" on a Canadian statement is no longer read as US dollars, and a KID's "7 USD" cost
> example no longer shows as a bare 7.00 that reads like a cost in francs.

## Description

### Context
- `numbers.py` and the statement parsers map every "$" to USD. The real Edward Jones statement in the
  corpus is Canadian ("Canadian Funds"): its amounts were labelled USD.
- `parse_kid` reads the cost example ("Costi totali 7 USD" on a USD 10 000 example, iShares S&P 500 IT
  KID) with no currency. Check values then shows "Costi totali 7.00" with no currency, which reads as a
  cost, and the Costs page formula says only "example on a 10'000 investment".

### User Flow Impact
Amounts in "$" carry CAD, AUD, SGD, HKD or NZD when the document names that dollar; when it names more
than one, the amount has no currency, needs review, and the document warns. The KID example shows as
"USD 7" with its currency.

### Performance / Efficiency Impact
One regex pass over the document text when a fact was read from a bare "$". No measurable impact.

### Proposed Approach
1. `parsers._dollar_currency` / `_resolve_dollars` after extraction: re-label facts read from a bare "$".
2. `parsers._example_currency` for the KID illustration (amount cell, else the "10 000" example line).
3. `analysis.py`: the illustration atom's formula names that currency. No amount or counting change.

### Risks & Follow-ups
- A US statement that mentions "Canadian" funds in a footnote would now be read as CAD. Checked on the
  Fidelity US statement: unchanged (34/34 holdings, USD).

## Acceptance Criteria

- [x] #1 Edward Jones statement amounts read as CAD; iShares IT KID example reads USD 7 (unit tests on SYNTHETIC lines)
- [x] #2 Statement scorer unchanged (Fidelity US 34/34 USD) and `python -m pce.evaluation` gates still pass

## Implementation Notes

## Outcome

- **Status**: Done.
- A bare "$" takes the one dollar the document names (CAD, AUD, SGD, HKD, NZD; "US$" next to another
  dollar resolves to the other one). No named dollar keeps USD. Several named dollars: no currency,
  `needs_review` with reason `dollar_unclear`, and a document warning.
- Real public statements (local only, not in git): Edward Jones amounts now CAD; Fidelity US unchanged
  (34/34 holdings, USD); statement scorer otherwise unchanged.
- KID cost example keeps its currency: iShares IT "USD 7", FR "EUR 13", DE "USD 20". The Costs formula
  reads "manufacturer example: USD 7 on a USD 10'000 investment". No amount or counting change.
- `python -m pce.evaluation` synthetic gates PASS; `tests/test_currency_misreads.py` passes.

## Issues Encountered

- None.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/sc-5.19-currency-misreads | f37f5e8 | 2026-11-13 | "$" and KID examples keep their currency |
