---
id: SC-8.23
title: Never show CHF 0 for assets that are not valued yet
status: To Do
assignee: []
owner: ""
model: ""
progress: 0
branch: ""
pr: ""
created_date: "2026-11-13 14:25"
updated_date: "2026-11-13 14:25"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/components/Shell.tsx
  - frontend/src/pages/crm/Contact.tsx
  - frontend/src/pages/Documents.tsx
  - frontend/src/lib/format.ts
  - frontend/src/lib/format.test.ts
  - frontend/src/lib/it.ts
spec_ref: CLAUDE.md (product principle "Missing is never zero")
rule_refs: [".claude/rules/frontend.md", ".claude/rules/finance.md"]
---

> **One-liner**: when no position is valued in CHF, the review header, the CRM contact and the "What we need" panel say "not valued yet" instead of "CHF 0".

## Description

### Context
With a statement in a currency that has no CHF rate on the documents (for example the public AJ Bell report in GBP),
no holding is valued and `aum.total` is `0`. The review header then shows `CHF 0` next to the badge
"No position valued in CHF yet", the CRM contact shows "Assets CHF 0", and the "What we need" panel shows
`CHF 0` per bank. That reads as a portfolio worth zero and breaks the rule that missing is never zero.

### User Flow Impact
The analyst sees "Assets not valued yet" (Italian: "Patrimonio non ancora valutato") where an amount cannot be computed.

### Performance / Efficiency Impact
No measurable impact.

### Proposed Approach
1. One helper that formats an asset amount only when at least one position is valued, else returns the "not valued yet" label.
2. Use it in `Shell.tsx`, `crm/Contact.tsx` and the per-bank line in `Documents.tsx`.
3. Italian string in `it.ts`; unit test for the helper.

### Risks & Follow-ups
- "1 banks" plural in the header is a separate wording bug, not fixed here.

## Acceptance Criteria

- [ ] #1 A review with no valued position shows "not valued yet" instead of CHF 0 in the header, contact and per-bank line
- [ ] #2 A review with valued positions still shows the CHF amount (test)

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered
