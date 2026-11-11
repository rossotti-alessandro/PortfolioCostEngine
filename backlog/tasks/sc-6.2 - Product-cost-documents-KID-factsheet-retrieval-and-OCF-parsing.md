---
id: SC-6.2
title: Product cost documents: KID/factsheet retrieval and OCF parsing
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - instruments
  - extraction
dependencies:
  - SC-6.1
  - SC-2.3
parent_task_id: SC-6
priority: P0
paths_owned:
  - "backend/src/pce/instruments/disclosures/**"
  - "backend/tests/integration/disclosures/**"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
  - ".claude/rules/extraction.md"
---

> **One-liner**: Find the dated official cost disclosure for each product and read its cost lines with evidence.

## Description

### Context

No product costs.

### User Flow Impact

Fund costs appear as 'estimated (KID dd.mm.yyyy)' with a link to the page.

### Performance / Efficiency Impact

Network-bound; cache by ISIN + document date.

### Proposed Approach

1. Allowlisted issuer hosts
2. Parse PRIIPs KID cost tables: ongoing, transaction, entry/exit, performance
3. Keep AMF-inside-OCF relation

### Risks & Follow-ups

See `docs/research/FEE_TAXONOMY.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 KID with OCF 1.08% incl. AMF 0.75% yields 1.08% economic, AMF as child
- [ ] #2 Illustrative cost example stored as illustrative, not observed

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
