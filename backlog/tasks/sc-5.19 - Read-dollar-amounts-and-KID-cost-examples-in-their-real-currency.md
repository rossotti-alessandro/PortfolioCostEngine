---
id: SC-5.19
title: Read "$" amounts and KID cost examples in their real currency
status: "In Progress"
assignee: []
owner: "Validate accuracy and speed up processing"
model: "claude-opus-5-5"
progress: 5
branch: "claude/sc-5.19-currency-misreads"
pr: ""
created_date: "2026-11-13 13:23"
updated_date: "2026-11-13 13:23"
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

- [ ] #1 Edward Jones statement amounts read as CAD; iShares IT KID example reads USD 7 (unit tests on SYNTHETIC lines)
- [ ] #2 Statement scorer unchanged (Fidelity US 34/34 USD) and `python -m pce.evaluation` gates still pass

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
