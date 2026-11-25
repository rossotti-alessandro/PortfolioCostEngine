---
id: SC-2.5
title: Extend fee taxonomy to all asset classes and MiFID cost categories
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-25 20:50"
updated_date: "2026-11-25 20:50"
labels:
  - research
  - finance
dependencies:
  - SC-2.4
parent_task_id: SC-2
priority: P2
paths_owned:
  - "data/taxonomy/fee_taxonomy.csv"
  - "docs/research/FEE_TAXONOMY.md"
  - ".claude/rules/finance.md"
spec_ref: docs/research/COST_PROTOCOL.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Give every cost a MiFID/FinSA category, a visibility and a payee, and add the asset classes the taxonomy lacks.

## Description

### Context

fee_taxonomy.csv covers bank fees, funds, structured products, wrappers and credit. It has no rows for listed and OTC derivatives, hedge funds, private markets, crypto, securities lending, cash drag, hedged share classes, bond mark-ups, ADR or corporate-action fees, and no column mapping to the MiFID II Annex II categories used by every ex-post report. finance.md lists 6 evidence statuses while ledger.Measurement has 8 (public_tariff, maximum).

### User Flow Impact

Ex-post bank reports reconcile line by line; family offices with alternatives see their fund-level fees as named categories instead of OTHER.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Add columns mifid_category (one_off|ongoing|transaction|ancillary|incidental; service|product), visibility (billed|embedded|implicit|tax|credit), payee (bank|manager|issuer|market|state).
2. Add the rows listed in COST_PROTOCOL.md section 2 with default status UNKNOWN or ESTIMATED.
3. Align finance.md status list with ledger.Measurement.
4. Update FEE_TAXONOMY.md and the vocab mapping only where codes are new.

### Risks & Follow-ups

Fee taxonomy semantics: needs Ale's per-PR approval (AGENTS.md rule 9).

## Acceptance Criteria

- [ ] #1 Every row has the three new columns filled
- [ ] #2 finance.md status list equals ledger.Measurement values
- [ ] #3 backlog-lint and the taxonomy loader tests stay green

## Implementation Notes

## Outcome

## Issues Encountered
