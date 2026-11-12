---
id: SC-5.10
title: Workflow arena - compare complete extraction workflows end to end
status: "In Progress"
assignee: []
owner: "Compare complete extraction workflows"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-rfm5yy"
pr: ""
created_date: "2026-11-12 13:10"
updated_date: "2026-11-12 13:04"
labels:
  - extraction
  - qa
dependencies:
  - SC-5.7
parent_task_id: SC-5
priority: P1
paths_owned:
  - "data/specimens/ocrbench/**"
  - "data/specimens/arena/**"
spec_ref: docs/adr/0003-document-extraction-and-ocr.md
rule_refs:
  - ".claude/rules/extraction.md"
  - ".claude/rules/privacy.md"
  - ".claude/rules/finance.md"
---

> **One-liner**: Run several complete extraction workflows, including an agentic one, on the same pages and SYNTHETIC prospects, and score them side by side with the accuracy protocol.

## Description

### Context

The model lab (SC-5.7) compares single models page by page. Ale asked whether we test complete workflows,
agentic or not, against each other. Today only the app's own workflow is scored end to end
(`pce.evaluation`), and the finder + verify workflow (SC-5.8, PR #15) is scored by a separate script.

### User Flow Impact

None directly. It decides which workflow the upload pipeline runs and how much reaches the analyst's review queue.

### Performance / Efficiency Impact

Benchmark only, run offline on CPU. Production code is unchanged.

### Proposed Approach

1. One runner that feeds every workflow the same inputs (54 real ocrbench pages, SYNTHETIC P-1042 and P-2077,
   digital and scanned) and scores them with `pce.evaluation` plus per-page fee recall/precision.
2. Workflows: (1) app today; (2) finder + verify; (3) finder + table structure from a layout model;
   (4) finder + a local vision model as second reader on scans and tables; (5) agentic: a local language
   model chooses tools, compares readers and flags doubts, but never writes or computes a number
   (every value must come from a tool with page and box).
3. Lab tab "Workflows": scores side by side, per-page differences, cost and speed, failure examples.

### Risks & Follow-ups

CPU only: the vision and agentic workflows run on a page subset. A local language model can still invent text;
the runner rejects any value not present in a tool output at the cited box.

## Acceptance Criteria

- [ ] #1 At least five complete workflows scored on the same inputs with the same scorer
- [ ] #2 The agentic workflow never emits a number that no tool read at its cited box (tested)
- [ ] #3 Lab shows the comparison with per-page drill-down; synthetic data labelled

## Implementation Notes

## Outcome

- **Status**:

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
