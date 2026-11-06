---
id: SC-1.1
title: Multi-agent dev protocol, backlog and claim scripts
status: "Done"
assignee: []
owner: "Set up multi-agent dev protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-pd19xu"
pr: ""
created_date: "2026-11-06 15:05"
updated_date: "2026-11-06 15:04"
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

- [x] #1 Two concurrent agent-start.sh runs on one story: exactly one wins (tested against origin)
- [x] #2 backlog-lint passes on all seeded stories and fails on a malformed one
- [x] #3 local-gate.sh prints GATE PASSED on this branch

## Implementation Notes

## Outcome

- **Status**: completed
- AGENTS.md, CLAUDE.md, docs/WORKFLOW.md, docs/SOURCES_OF_TRUTH.md, `.claude/rules/*` (finance, extraction, privacy, frontend, task-lifecycle, testing)
- ADRs 0001-0005 and docs/design/DESIGN_SYSTEM.md
- Scripts: agent-start/teardown (branch-based claims, release commits), claims-status, backlog-new-id/set/board/lint, local-gate, bootstrap, setup-hooks
- Git hooks (conventional commits, secret and client-document guard, ruff, fast gate on push), CI running the same gate, PR template
- Backlog: 11 epics, 39 stories; skills caveman, ponytail, ponytail-review vendored in `.agents/skills`

## Issues Encountered

- Cloud proxy refuses ref deletion (HTTP 403): claims are released with a "release" commit instead of deleting the branch.
- Claude Code project hooks in `.claude/settings.json` were blocked by the session's safety classifier; `updated_date` is stamped by `backlog-set.mjs` instead.
- Test claim branch `claims/sc-0.0` left on origin (released); safe to delete from a laptop.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-pd19xu | b2d585f | 2026-11-06 | chore: multi-agent dev protocol, backlog and extraction toolchain |
| claude/project-thread-pd19xu | 22eb579 | 2026-11-06 | fix(infra): release claims with a commit, not a branch delete |
| claude/project-thread-pd19xu | c9a6b3a | 2026-11-06 | fix(infra): skip push gate on backlog-only pushes |
