---
id: SC-8.16
title: Costs page answer first and unknowns listed once
status: "Done"
assignee: []
owner: "Redesign FeeLens user flow and components"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-bj3sap"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/37"
created_date: "2026-11-12 23:52"
updated_date: "2026-11-12 23:58"
labels:
  - ui
dependencies: []
parent_task_id: SC-8
priority: P1
paths_owned:
  - frontend/src/pages/Costs.tsx
  - frontend/src/components/ReadSummary.tsx
  - frontend/src/lib/it.ts
  - docs/design/DESIGN_SYSTEM.md
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs: [".claude/rules/frontend.md", ".claude/rules/finance.md"]
---

> **One-liner**: The Costs page opens with the answer in one sentence and lists each undetermined cost once, as the document to ask for.

## Description

### Context
Design canvas board "Costs with the evidence panel" (thread "Redesign FeeLens user flow and components"):
https://claude.ai/artifact/KLMvQa2NbwCHhYsibvgRnj. On main the page starts with four equal figure cards,
so the answer (what the client pays a year, and that it is a lower bound) has no more weight than the
assets figure. The five undetermined costs appear three times: as review points, as red chips under the
layer chart and as the "What is missing" requests further down. Ale asked to continue with the simpler
Costs page (2026-11-12 23:46 UTC).

### User Flow Impact
- Answer card: "Known annual cost today · at least", the total large and clickable to its calculation, then
  one sentence with % and bps of assets, banks and positions, and how many costs are not determined ("so the
  real figure is higher; nothing unknown is counted as zero"). On the right: debited from the accounts,
  inside fund and product prices (both clickable to their lines), evidence coverage.
- "Documents to ask for" (was "What is missing") comes right after, ranked by assets affected.
- Points to review no longer repeat the undetermined costs when a request covers them; the chips under the
  chart are gone (the chart rows still say "+ not determined"). The read summary counts the same way and
  adds the number of documents to ask for.

### Performance / Efficiency Impact
None: same analysis payload, less markup.

### Proposed Approach
1. `Costs.tsx`: `Answer` card replaces the four figure cards; section order requests → points → chart →
   ledger → folds; drop the unknown chips.
2. `ReadSummary.tsx`: same point count as the page, plus documents to ask for. EN/IT strings.

### Risks & Follow-ups
- Unknowns stay visible in the answer sentence, the requests, the chart rows and the ledger; if the server
  sends no request (none derivable), the review points still list every unknown.
- Breakdown tabs (chart, checks, positions) from the canvas are a later step.

## Acceptance Criteria

- [x] #1 The page opens with the known annual cost, its lower-bound wording and the count of undetermined costs; the total opens its calculation
- [x] #2 Each undetermined cost is listed once in the to-do (as a request when one exists), never shown as zero
- [x] #3 E2E suite passes (costs, trace, review points)

## Implementation Notes

- Owned paths as listed. No backend change; `not_determined` review points are hidden only when the
  analysis carries at least one request, so an unknown without a request is still listed as a point.

## Outcome

- **Status**: completed
- `Answer` card replaces the four figure cards; "Documents to ask for" follows; the unknown chips under the
  chart are gone; the read summary counts points the same way and shows the documents to ask for.
- E2E 17/17 passed locally; `local-gate.sh` GATE PASSED. Screenshot: project files
  `feelens-redesign/costs-answer.png`.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-bj3sap | d64e862 | 2026-11-12 | Answer card, documents to ask for, unknowns listed once |
| claude/project-thread-bj3sap | dd99cd4 | 2026-11-12 | Design system: Costs layout |

## Issues Encountered
