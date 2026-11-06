# ADR 0005 — Multi-agent delivery protocol

Status: Accepted, 2026-11-06.

## Context

Several AI sessions (Claude Code threads, Codex, Cursor, cloud and laptop) build this repo at once. The
handoff kit proposed a single `backlog.json` and noted, correctly, that local claim files are not locks.
FoodAppTracker (Ale's other project) already runs a protocol that works in practice: markdown stories with
frontmatter, atomic remote claims, generated board, local gate as CI equivalent. Its claim refs
(`refs/agent-claims/*`) are refused by cloud egress proxies, so cloud sessions there fall back to a weaker claim.

## Decision

- **Backlog** = `backlog/tasks/sc-<id> - <Title>.md` (YAML frontmatter + template body). Epics `SC-<n>`,
  stories `SC-<n>.<m>`. One file per story avoids merge conflicts that a single JSON file guarantees.
- **Claims** = remote branches `claims/sc-<id>` whose tip commit is either `claim …` or `release …`.
  `scripts/agent-start.sh` pushes a claim commit on top of a release tip (or creates the branch); a
  concurrent second push is rejected as non-fast-forward. Release is a new commit, not a deletion, because
  the cloud proxy refuses ref deletion (observed 2026-11-06, HTTP 403). One mechanism for laptops and cloud.
- **Id reservation** = remote branches `backlog-ids/sc-<id>` via `scripts/backlog-new-id.mjs`.
- **Liveness** from remote evidence only (`scripts/claims-status.mjs`, 48 h TTL). Stale claims are released
  by the coordinator, never stolen.
- **Ownership**: each story declares `paths_owned`; shared contracts are serialised (AGENTS.md rule 4).
- **Gate**: `scripts/local-gate.sh` is the single definition of "green", used by hooks, CI and humans.
- **Merge**: squash into `main`; agents may self-merge except the categories in AGENTS.md rule 9.
- **Agent style**: caveman (lite) for replies to people, ponytail for code, ponytail-review for review,
  vendored in `.agents/skills/`.

## Consequences

- Claim branches stay on the remote (one per story ever claimed, each a short chain of empty commits). A
  maintainer can prune released ones from a laptop with `git push origin --delete claims/sc-<id>`.
- `backlog/BOARD.md` is regenerated only on main, so it can lag a few minutes behind open branches;
  `claims-status.mjs` is the live view.

## Alternatives rejected

- GitHub Issues as the board: good, but agents in some sessions cannot write issues reliably and the
  story text would live outside the repo history. Can be mirrored later.
- `backlog.json` from the kit: one file edited by everyone, conflicts on every claim.
