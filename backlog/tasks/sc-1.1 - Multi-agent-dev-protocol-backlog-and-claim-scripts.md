---
id: SC-1.1
title: Multi-agent dev protocol, backlog and claim scripts
status: In Progress
assignee: []
owner: "Set up multi-agent dev protocol"
model: "claude-opus-5-5"
progress: 90
branch: "claude/project-thread-pd19xu"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:05"
labels:
  - infra
  - docs
dependencies: []
parent_task_id: SC-1
priority: P0
paths_owned:
  - "AGENTS.md"
  - "CLAUDE.md"
  - "docs/WORKFLOW.md"
  - "docs/SOURCES_OF_TRUTH.md"
  - "docs/adr/**"
  - "backlog/**"
  - "scripts/**"
  - ".githooks/**"
  - ".github/**"
  - ".claude/**"
  - ".agents/**"
  - "skills-lock.json"
spec_ref: docs/adr/0005-multi-agent-protocol.md
rule_refs:
  - ".claude/rules/task-lifecycle.md"
---

> **One-liner**: Give every agent the same rules, backlog and atomic claim so parallel threads never collide.

## Description

### Context

Empty repo; the ChatGPT kit had a single backlog.json and acknowledged it had no real lock. FoodAppTracker's protocol works but its claim refs are refused in cloud sessions.

### User Flow Impact

No user-facing change. Agents can see what is claimable, claim atomically and know the gate.

### Performance / Efficiency Impact

No measurable impact.

### Proposed Approach

1. Port FoodAppTracker scripts with SC ids and branch-based claims
2. Write AGENTS.md, CLAUDE.md, WORKFLOW, rules, ADRs 0001-0005
3. Seed epics and stories from the kit, re-scoped
4. Hooks, PR template, CI running the same gate

### Risks & Follow-ups

See `docs/adr/0005-multi-agent-protocol.md` and the rules listed in `rule_refs`.

## Acceptance Criteria

- [ ] #1 Two concurrent agent-start.sh runs on one story: exactly one wins (tested against origin)
- [ ] #2 backlog-lint passes on all seeded stories and fails on a malformed one
- [ ] #3 local-gate.sh prints GATE PASSED on this branch

## Implementation Notes

## Outcome

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
