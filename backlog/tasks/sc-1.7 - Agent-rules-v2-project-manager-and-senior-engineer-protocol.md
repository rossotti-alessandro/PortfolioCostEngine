---
id: SC-1.7
title: "Agent rules v2: project manager and senior engineer protocol"
status: "Done"
assignee: []
owner: "Update Claude rules and dev protocol"
model: "claude-opus-5-5"
progress: 100
branch: "claude/project-thread-ph3wca"
pr: "https://github.com/rossotti-alessandro/PortfolioCostEngine/pull/54"
created_date: "2026-11-13 23:55"
updated_date: "2026-11-14 00:06"
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
  - "scripts/backlog-board.mjs"
  - "docs/adr/0002-design-system.md"
  - "docs/research/UX_RECOMMENDATIONS.md"
  - ".github/PULL_REQUEST_TEMPLATE.md"
  - "backlog/TEMPLATE.md"
  - "backlog/config.yml"
  - "backlog/BOARD.md"
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

- [x] #1 Every contradiction listed in Context is resolved in exactly one canonical file
- [x] #2 Existing hard rules (fees never invented, missing is not zero, no double counting, synthetic data labelled, no margin in client output, no PyMuPDF, Decimal money, simple UI, EN + IT) are all still present
- [x] #3 `./scripts/local-gate.sh` prints GATE PASSED

## Implementation Notes

- Rewrote: AGENTS.md (PM loop, cloud branch rule, rule-9 list and ask, dependency and external-skill
  policy, board in the story PR), CLAUDE.md (product rules, engineering standards, status list and
  types/i18n paths as in the code), rules finance/frontend/extraction/testing/task-lifecycle, new
  `.claude/rules/deck.md`, WORKFLOW, PR and story templates, DoD in `backlog/config.yml`, HANDOFF §5,
  SOURCES_OF_TRUTH, ADR 0005 addendum; ADR 0002 and UX_RECOMMENDATIONS note EN + IT.
- 2026-11-14 11:05: "Results stay fresh" section added at Ale's request (dated results, refresh memory, docs and artifacts after a merge that changes a number).
- Merge, not rebase, to bring `main` into a pushed branch: `.claude/settings.json` denies force-push.
- `scripts/backlog-board.mjs`: header text only (where the board is regenerated).
- Not changed: `.claude/settings.json`. Widening the permission allowlist was refused by the session's
  safety check; left for Ale to decide.

## Outcome

- **Status**: completed
- Evidence for #1: drift items from Context, each resolved in one file (cloud branch: AGENTS rule 2 +
  WORKFLOW §2; board PRs: AGENTS § lifecycle + task-lifecycle; story closing: task-lifecycle step 4;
  bundling: AGENTS rule 2; HANDOFF: refreshed + PR template; languages: frontend.md; simplicity:
  CLAUDE § Product rules + frontend.md; rule 9 asks and dependencies: AGENTS rule 9 + WORKFLOW §6;
  accuracy evidence: extraction.md; deck: deck.md).
- Evidence for #2: each hard rule grepped in CLAUDE.md / AGENTS.md / .claude/rules (PR Verification).

## Issues Encountered

- SC-9.6 is still To Do on `main` although PR #34 delivered it; recorded in HANDOFF §5, left to its owner.
- PR #48 bundles several SC-11 stories; the new rule 2 applies to new PRs.

## Branch & Commits

| Branch | Hash | Date | Description |
| ------ | ---- | ---- | ----------- |
| claude/project-thread-ph3wca | 0cf260f | 2026-11-13 23:55 | story file |
| claude/project-thread-ph3wca | 9db3af5 | 2026-11-13 23:57 | AGENTS, CLAUDE, finance rules |
| claude/project-thread-ph3wca | 166ecd9 | 2026-11-13 23:58 | frontend, extraction, testing, deck rules |
| claude/project-thread-ph3wca | 9267269 | 2026-11-14 00:00 | WORKFLOW, templates, HANDOFF, ADR 0005 |
| claude/project-thread-ph3wca | 3582454 | 2026-11-14 00:01 | board header, EN + IT notes |
