# Story template

Reserve an id first: `node scripts/backlog-new-id.mjs --parent SC-<epic>`. Save as
`backlog/tasks/sc-<id> - <Title-With-Dashes>.md`. Replace every `<!-- -->` placeholder.
`node scripts/backlog-lint.mjs` checks the shape.

```markdown
---
id: SC-<epic>.<n>
title: <what changes, ≤ 70 chars>
status: To Do
assignee: []
owner: "" # thread/session title while someone is on it (set by agent-start.sh)
model: "" # model of the owner session
progress: 0 # 0-100, bump with every commit via scripts/backlog-set.mjs
branch: ""
pr: ""
created_date: "YYYY-MM-DD HH:MM"
updated_date: "YYYY-MM-DD HH:MM"
labels:
  - <area>
dependencies: [] # story ids that must be Done first
parent_task_id: SC-<epic>
priority: P0 | P1 | P2 | P3
paths_owned:
  - <glob this story may edit>
spec_ref: <doc that defines the behaviour, e.g. docs/research/FEE_TAXONOMY.md>
rule_refs: [] # e.g. [".claude/rules/finance.md"]
---

> **One-liner**: <!-- one sentence: what this adds or fixes and why it matters to a user now -->

## Description

### Context
<!-- current state, what is missing or broken, where -->

### User Flow Impact
<!-- what an analyst or prospect sees differently -->

### Performance / Efficiency Impact
<!-- latency, memory, model cost; "no measurable impact" is fine but must be explicit -->

### Proposed Approach
<!-- numbered steps naming files/functions -->

### Risks & Follow-ups

## Acceptance Criteria

- [ ] #1 <!-- success condition, testable -->
- [ ] #2 <!-- regression guard -->

## Implementation Notes

## Outcome

- **Status**: completed | partial | blocked

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
```

Rules: one-liner required · ≥ 2 numbered criteria (success + regression guard) · `paths_owned` disjoint from
other In Progress stories · Done only with real hashes from `git log --oneline` · dates absolute, UTC.
