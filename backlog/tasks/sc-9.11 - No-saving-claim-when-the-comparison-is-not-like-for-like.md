---
id: SC-9.11
title: No saving claim when the comparison is not like for like
status: "In Progress"
assignee: []
owner: "Improve CRM UX, camera scan and access control"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-m6dkdk"
pr: ""
created_date: "2026-11-25 22:20"
updated_date: "2026-11-25 22:16"
labels:
  - finance
dependencies: []
parent_task_id: SC-9
priority: P1
paths_owned:
  - "backend/src/pce/finance/scenarios.py"
  - "backend/src/pce/analysis.py"
  - "backend/src/pce/api.py"
  - "backend/src/pce/report.py"
spec_ref: docs/research/FEE_TAXONOMY.md
rule_refs:
  - ".claude/rules/finance.md"
---

> **One-liner**: Record, after the fact, the `Comparison.saving_claimed` flag that Cursor commit 3825346 added without a story: no saving is shown when today's books are unvalued or the proposal is not comparable.

## Description

### Context

Cursor commit 3825346 (pushed to main on 2026-11-25 without a story or PR) added
`saving_claimed: bool = True` to `Comparison` in `finance/scenarios.py`. `analysis.py` sets it to False
when the comparison cannot support a saving; `api.py` then returns `saving: null` and `report.py` drops
the saving sentence. Flagged in SC-9.9 as a shared finance contract changed without a story. Ale decided
on 2026-11-25 to keep it ("Yes all of them if they are improvements", reply to the coordinator's question).

### User Flow Impact

When the current books are not valued, the client report and the dashboard show no saving instead of a
saving computed against an incomplete side. Applies the product principle "no comparable service, no
savings claim".

### Performance / Efficiency Impact

None.

### Proposed Approach

No code change: the behaviour is on main and covered by the Cursor commit's tests in
`backend/tests/test_extraction_correctness.py`. This story records the decision and its origin.

### Risks & Follow-ups

None.

## Acceptance Criteria

- [x] #1 Ale's decision to keep the flag is recorded with the commit that introduced it

## Implementation Notes

Backlog record only.

## Outcome

- **Status**: completed (kept as shipped in 3825346, decision recorded)

## Issues Encountered

Work done outside the protocol (Cursor, straight to main) leaves finance contract changes without a story;
AGENTS.md already requires claim, branch and PR for every tool.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| main | 3825346 | 2026-11-25 | Cursor: treat a missing KID as unknown, add Comparison.saving_claimed |
