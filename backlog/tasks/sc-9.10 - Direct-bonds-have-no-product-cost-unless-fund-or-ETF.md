---
id: SC-9.10
title: Direct bonds have no product cost unless fund or ETF
status: Done
assignee: []
owner: "Improve CRM UX, camera scan and access control"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-m6dkdk"
pr: ""
created_date: "2026-11-25 22:10"
updated_date: "2026-11-25 22:06"
labels:
  - finance
dependencies: []
parent_task_id: SC-9
priority: P1
paths_owned:
  - "backend/src/pce/analysis.py"
  - "backend/tests/test_kid_join.py"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: A directly held bond with a valid ISIN no longer gets an "unknown ongoing charge"; it has none, unless its name says fund or ETF or a KID for its ISIN is uploaded.

## Description

### Context

Cursor commit 3825346 made `_product_gap` treat every non-equity, non-cash holding with a valid ISIN as a
product whose missing KID is an UNKNOWN ongoing charge. A plain bond has no ongoing charge, so any
portfolio holding bonds could never be reported complete. Raised in SC-9.9; Ale approved on 2026-11-25
("Yes all of them if they are improvements", reply to the coordinator's question on directly held bonds).

### User Flow Impact

Portfolios with plain bonds stop showing a "not determined" product cost per bond.

### Performance / Efficiency Impact

None.

### Proposed Approach

`_product_gap` returns False for class BOND, as for EQUITY and CASH. Bond funds are classed FUND by name
("fund", "FD", "SICAV" are checked before the bond words) and bond ETFs ETF, so they keep the unknown atom.
A KID uploaded for the bond's exact ISIN still turns it into a FUND (existing join rule).

### Risks & Follow-ups

A bond fund whose name has none of the fund words and no KID would now show no product cost. Same
trade-off as equities; the KID join covers it once the KID is uploaded.

## Acceptance Criteria

- [x] #1 A plain bond with a valid ISIN and no KID has no FUND_ONGOING or PRODUCT_UNKNOWN atom
- [x] #2 A bond fund (name says fund) with no KID still has an unknown ongoing charge, never zero
- [x] #3 A bond with a KID for its ISIN still counts the KID's ongoing charge

## Implementation Notes

## Outcome

- **Status**: completed
- `_product_gap` treats BOND like EQUITY and CASH. Three tests in `backend/tests/test_kid_join.py`. Gate: GATE PASSED (pytest 289 passed / 4 skipped, vitest 28).

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-m6dkdk | 924cde4 | 2026-11-25 | BOND excluded from the product-cost gap, tests |
