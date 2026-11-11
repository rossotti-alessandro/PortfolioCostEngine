---
id: SC-8.1
title: Design system tokens, house components and app shell
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
  - ui
dependencies: []
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/styles/**"
  - "frontend/src/components/**"
  - "frontend/src/app/shell/**"
  - "frontend/package.json"
  - "frontend/pnpm-lock.yaml"
spec_ref: docs/design/DESIGN_SYSTEM.md
rule_refs:
  - ".claude/rules/frontend.md"
---

> **One-liner**: Build the tokens and shared components once so every screen looks and behaves the same.

## Description

### Context

No frontend.

### User Flow Impact

Consistent navy/teal private-bank look, stepper, status chips, money formatting.

### Performance / Efficiency Impact

Bundle budget: < 300 kB gzipped initial.

### Proposed Approach

1. Vite + React + TS + Tailwind v4 + shadcn/ui init
2. tokens.css per DESIGN_SYSTEM § 1-3
3. Money, Bps, StatusChip, EvidenceLink, CoverageMeter, GapCard, Stepper, DemoWatermark
4. i18n scaffold it/de/en

### Risks & Follow-ups

See `docs/design/DESIGN_SYSTEM.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Money renders null as 'Not determined' (unit test)
- [ ] #2 Contrast of every token pair ≥ AA (script)
- [ ] #3 Storybook-like gallery page lists all house components

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
