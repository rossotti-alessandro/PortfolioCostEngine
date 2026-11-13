---
id: SC-1.7
title: "Agent rules v2: project manager and senior engineer protocol"
status: "In Progress"
assignee: []
owner: "Update Claude rules and dev protocol"
model: "claude-opus-5-5"
progress: 5
branch: "claude/project-thread-ph3wca"
pr: ""
created_date: "2026-11-13 23:55"
updated_date: "2026-11-13 23:55"
labels:
  - docs
dependencies: []
parent_task_id: SC-1
priority: P1
paths_owned:
  - "CLAUDE.md"
  - "AGENTS.md"
  - "HANDOFF.md"
  - "docs/WORKFLOW.md"
  - "docs/SOURCES_OF_TRUTH.md"
  - "docs/adr/0005-multi-agent-protocol.md"
  - ".claude/rules/**"
  - ".claude/settings.json"
  - ".github/PULL_REQUEST_TEMPLATE.md"
  - "backlog/TEMPLATE.md"
  - "backlog/tasks/sc-1.7*"
spec_ref: AGENTS.md
rule_refs: [".claude/rules/task-lifecycle.md"]
---

> **One-liner**: Bring the agent rules in line with how a week of parallel threads actually worked, so every
> agent plans like a project manager, codes like a senior engineer and wastes no turns on protocol friction.

## Description

### Context

The protocol (SC-1.1, 2026-11-06) predates 50 PRs from up to eight parallel cloud threads. Observed drift:
cloud sessions must push to a mandated `claude/project-thread-*` branch, so the "one branch per story from
fresh main" rule is unworkable as written; board refreshes became separate PRs (#25, #31, #32, #51, #53,
two of them duplicates); merged stories stayed To Do on the board (SC-9.6 after PR #34), so the board offers
finished work as ready to claim; PR #48 bundles several stories; `HANDOFF.md` is two days stale; the
frontend rule says "Italian first, then German, English" while the product is EN + IT; Ale's UI simplicity
rule lives only in HANDOFF; rule 9 does not say how to ask Ale or that new runtime dependencies need him;
accuracy evidence for extraction changes and the deck-from-app-screenshots loop have no written rule.

### User Flow Impact

None for analysts. Agents get one clear path from request to merged PR, and Ale gets fewer, clearer asks.

### Performance / Efficiency Impact

Fewer PRs per story (no separate board PR), fewer permission prompts, less re-reading of stale docs.

### Proposed Approach

1. AGENTS.md: cloud branch rule, PM loop (plan, scope, verify, report), rule 9 asks, story-in-PR closing,
   board in the same PR, dependency and external-skill policy.
2. CLAUDE.md: senior-engineer standards (boundaries, errors, logging, tests, performance, security),
   product rules in one place, read-first table updated.
3. Rules: frontend (EN + IT, simplicity), extraction (accuracy evidence), new `deck.md`, testing.
4. WORKFLOW, PR template, story template, settings allowlist, HANDOFF pointer refresh, ADR 0005 addendum.

### Risks & Follow-ups

- Rule files are shared contracts (AGENTS.md rule 4): this PR is the only one touching them.
- Script changes (board excluding claimed stories, CI board refresh) stay in SC-1.4.

## Acceptance Criteria

- [ ] #1 Every contradiction listed in Context is resolved in exactly one canonical file
- [ ] #2 Existing hard rules (fees never invented, missing is not zero, no double counting, synthetic data labelled, no margin in client output, no PyMuPDF, Decimal money, simple UI, EN + IT) are all still present
- [ ] #3 `./scripts/local-gate.sh` prints GATE PASSED

## Implementation Notes

## Outcome

- **Status**: completed | partial | blocked

## Issues Encountered

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
