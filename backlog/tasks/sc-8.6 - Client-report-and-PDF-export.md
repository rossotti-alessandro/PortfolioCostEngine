---
id: SC-8.6
title: Client report and PDF export
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
  - report
dependencies:
  - SC-8.4
  - SC-8.5
  - SC-7.5
parent_task_id: SC-8
priority: P0
paths_owned:
  - "frontend/src/routes/report/**"
  - "backend/src/pce/report/**"
spec_ref: docs/research/UX_RECOMMENDATIONS.md
rule_refs:
  - ".claude/rules/frontend.md"
  - ".claude/rules/privacy.md"
---

> **One-liner**: Give the prospect a clear, honest one-page summary with an evidence appendix.

## Description

### Context

No report.

### User Flow Impact

Download a PDF with approved figures, assumptions, caveats, and a DEMO watermark when synthetic.

### Performance / Efficiency Impact

Export < 5 s.

### Proposed Approach

1. Report layout separate from analyst shell
2. Server-side PDF render
3. Only approved figures

### Risks & Follow-ups

See `docs/research/UX_RECOMMENDATIONS.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Report contains no internal margin (test on payload and PDF text)
- [ ] #2 Synthetic dataset always prints the SYNTHETIC DEMO watermark

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
