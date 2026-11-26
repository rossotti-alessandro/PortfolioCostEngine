---
id: SC-7.16
title: Idempotent merge of repeated documents and cost per asset class
status: Done
assignee: []
owner: "Cover costs for every asset type"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-xhgbxu"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/79"
created_date: "2026-11-26 00:15"
updated_date: "2026-11-26 00:25"
labels:
  - finance
dependencies: []
parent_task_id: SC-7
priority: P0
paths_owned:
  - "backend/src/pce/finance/scenarios.py"
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/instruments/registry.py"
  - "backend/tests/test_merge_idempotency.py"
  - "backend/tests/test_asset_classes.py"
  - "backend/tests/test_extraction_correctness.py"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Uploading a statement, KID or termsheet twice, or holding one ISIN in two lots, no longer crashes the analysis or doubles assets, and every asset type gets the right product-cost rule.

## Description

### Context

Measured on the synthetic P-1042 pack (2026-11-26): adding a second copy (other bytes, same content) of
the portfolio statement, of any KID or of the termsheet makes `analyse()` raise
`InclusionGraphError: duplicate atom id`, so the analyst sees no result at all. Byte-identical files are
already refused at upload (sha256), but a re-download or re-export has other bytes. The same crash
happens when one ISIN appears twice at one institution (two lots or two sub-accounts), because
`product_atoms()` keys atoms by institution + ISIN + fee code. Name rules also misclass common holdings:
"US Treasury Note" and "Global Convertible Bond Fund" become structured products, and listed options,
futures and physical metals with an ISIN are asked for a KID and marked as an unknown fund charge.
The CFI mapping sends mini-futures (RF) to no class and options/futures (O, F) to the name rule.

Out of scope (thread "Audit cost categories for consistency"): fee lines in the cost-report and
cash-debit loops, `LAYER_BY_CODE`, SP entry cost amortisation.

### User Flow Impact

The analyst can upload a document again without breaking the prospect; the result is the same as with
one copy, and a check says which copy was ignored. Options, futures and metals no longer create a
false "KID missing" request.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. `product_atoms()`: merge holdings with the same account + instrument before rate × value.
2. `analyse()`: a portfolio statement with the same institution, valuation date and position set as an
   earlier one is a duplicate: ignored, with a check. Positions are not doubled.
3. KID/termsheet join: one document per ISIN, newest `as_of` first, lowest id on a tie; other copies are
   reported in a check, and differing figures between them are a warning.
4. `infer_asset_class()`: fund and bond words beat the weak structured words (note, tracker,
   convertible); new classes DERIVATIVE and COMMODITY with no product cost; CFI O/F/RF mapped.
5. Tests: per asset class, and idempotency properties (duplicate document, shuffled input order, re-run).

### Risks & Follow-ups

Touches finance/ (product cost per asset class): needs Ale's per-PR approval (AGENTS.md rule 9).

## Acceptance Criteria

- [x] #1 A second copy of any document in the P-1042 pack gives the same total, AUM and unknown list as one copy
- [x] #2 One ISIN in two lots at one bank gives one product atom on the summed value
- [x] #3 Shuffling documents and facts gives the same result; a re-run is identical
- [x] #4 Each asset class (equity, ETF, fund, bond, structured, derivative, commodity, cash) has a test of its product-cost rule
- [x] #5 Existing pinned P-1042 figures unchanged; gate green

## Implementation Notes

- Merge in `product_atoms()` (all callers, incl. the optimised scenario where two swapped lots map to one
  proposal fund) and `_merge_lots()` in `analysis.py` for the unknown-cost path and KID requests.
- Statement duplicate = same institution, `as_of` and multiset of (ISIN or label, value, currency).
  Two accounts at one bank with different positions stay separate.
- `_pick_product_docs()`: newest `as_of`, lowest id on a tie; check `duplicate:product:<ISIN>` is info
  when the copies agree, warn when their figures differ.
- Asset class: a public-register class (`asset_class_source` set by SC-6.3) is authoritative; a bank
  category column is the exposure, so a fund/ETF/certificate name wins over Equities/Bonds/Commodities.
  New classes DERIVATIVE and COMMODITY have no product cost. One existing test expectation changed:
  `infer_asset_class("Xtrackers ... ETF", "EQUITY")` is ETF unless the class came from a register.
- Re-ran the class rule over the 128 positions read from the 5 real public statements in the corpus:
  0 changed. Repeated-document repro on the P-1042 pack: every copy (statement, KIDs, termsheet,
  tariffs, cash statement) leaves the total at CHF 61,449.60 and AUM at CHF 4,300,000. A repeated cost
  report still crashes: owned by SC-7.15.

## Outcome

- **Status**: completed
- Repeated statements, KIDs, termsheets and lots no longer crash or double count; shuffled input and
  re-runs give byte-identical output; every asset class has a tested product-cost rule.

## Issues Encountered

- Same cost report uploaded twice still raises duplicate atom id; split to SC-7.15 (other thread).

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-xhgbxu | f75d838 | 2026-11-26 | fix(finance): count a repeated statement, KID or lot once |
| claude/project-thread-xhgbxu | 0f93980 | 2026-11-26 | fix(finance): product-cost rule for every asset class |
