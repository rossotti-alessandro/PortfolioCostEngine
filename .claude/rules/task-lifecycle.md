---
description: Backlog story lifecycle. Template, required fields, claim, progress, Done, board.
paths:
  - "backlog/**"
---

# Story lifecycle

Template: [backlog/TEMPLATE.md](../../backlog/TEMPLATE.md). Protocol: [AGENTS.md](../../AGENTS.md).

## Shape

- **Epic**: label `epic`, id `SC-<n>`. Status and % are computed from its stories by
  `scripts/backlog-board.mjs`; never hand-set.
- **Story**: id `SC-<epic>.<n>`, ≤ 1 day, one PR, disjoint `paths_owned`. Bigger → split.
- New ids are reserved, never guessed: `node scripts/backlog-new-id.mjs --parent SC-<epic>`.
- File name: `backlog/tasks/sc-<id> - <Title-With-Dashes>.md`.
- Required: one-liner, User Flow Impact, Performance Impact, ≥ 2 numbered acceptance criteria
  (`- [ ] #1 …`: success + regression guard), `paths_owned`, `dependencies`, `priority` P0–P3.
  `node scripts/backlog-lint.mjs` enforces it.
- Acceptance criteria are observable: a test name, a command and its expected output, a number with
  its corpus, or a screenshot (EN and IT for UI). "Works better" is not a criterion.

## Work arriving as a request, not a story

A person's request in a thread is the usual start. Before code: find the story that covers it
(`grep -l` the board and `backlog/tasks/`) or reserve a new id and write the story, scoped to the gap
you verified. One request with several outcomes becomes several stories, delivered one PR each.

## Claim → work → close

1. Pick from `node scripts/backlog-board.mjs --ready` (or the story the person named). Check
   `node scripts/claims-status.mjs`: the board can list a story as ready that is claimed or already built.
2. `OWNER="<thread title>" AGENT_MODEL=<model> SLUG=<slug> ./scripts/agent-start.sh claude SC-<id>`
   (cloud session with a mandated branch: add `NO_WORKTREE=1`).
3. After each commit: `node scripts/backlog-set.mjs SC-<id> progress=<0-100>`; add the hash to
   `## Branch & Commits`. PR up: `node scripts/backlog-set.mjs SC-<id> pr=<url>`.
4. Before the PR merges, on the story branch: status Done (or In Progress if partial), Outcome and
   Branch & Commits filled, criteria ticked with their evidence. A squash merge drops commits pushed
   after it, so a story merged as To Do stays To Do on the board and is offered to the next agent.
5. Last commit of the PR: `node scripts/backlog-board.mjs` (after merging `origin/main` into the branch).
6. `./scripts/agent-teardown.sh --yes <worktree | SC-id>` releases the claim.

## Never

- Mark Done without real hashes from `git log --oneline`.
- Write relative dates. Use `YYYY-MM-DD HH:MM` (UTC) from the session clock.
- Edit `backlog/BOARD.md` by hand, or open a PR that only refreshes it. On a conflict, regenerate it.
- Edit another agent's story file, except to add a note under Issues Encountered that they should read.
- Fix an unrelated bug inline: reserve an id and file a story instead.
