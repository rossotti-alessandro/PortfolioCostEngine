# Workflow

The commands behind [AGENTS.md](../AGENTS.md). Works the same for Claude Code, Codex and Cursor, on a
laptop or in a cloud session.

## TL;DR

```bash
git fetch origin
node scripts/backlog-board.mjs --ready                     # pick a story
node scripts/claims-status.mjs                             # nobody LIVE on it?
OWNER="Fee ledger thread" AGENT_MODEL=claude-opus-5-5 SLUG=fee-ledger ./scripts/agent-start.sh claude SC-7.1
cd .claude/worktrees/claude-sc-7.1
# … change loop, commit + push each unit, node scripts/backlog-set.mjs SC-7.1 progress=40 …
# close the story file (status, Outcome, Branch & Commits), then:
./scripts/local-gate.sh                                    # GATE PASSED
# open the PR into main, paste the gate tail, merge per AGENTS.md rule 9
cd - && ./scripts/agent-teardown.sh --yes .claude/worktrees/claude-sc-7.1
```

## 1. Change loop

| Step | Do | Done when |
|---|---|---|
| Pinpoint | Reproduce the symptom, find the file and line | You can state the cause in one sentence |
| Test first | Write or find the test that shows it | It fails for the right reason |
| Fix | Smallest change that solves it (ponytail) | — |
| Retest | Same test | Passes |
| Regression | Module suite (`uv run pytest tests/unit/finance`, `pnpm test`) | Green |
| Commit | Conventional commit, why in the body; push | Hash in the story's Branch & Commits |

## 2. Branches and commits

- Story branch: `<agent>/sc-<id>-<slug>` from fresh `origin/main` (`claude/sc-7.1-fee-ledger`).
- Commit subject: `<type>(<scope>): <subject>` ≤ 72 chars. Types: feat fix refactor test chore docs perf deps ci build style revert.
  Scopes in use: `finance`, `extraction`, `intake`, `instruments`, `api`, `db`, `ui`, `report`, `backlog`, `infra`, `deps`, `docs`.
- Dependency bumps get their own `deps:` PR with the licence of every new package in the description.

## 3. Cloud sessions

- The session may mandate a branch name. Then claim with `NO_WORKTREE=1 ./scripts/agent-start.sh claude SC-<id>`
  on that branch; the story's `branch:` field links it.
- Pushes to custom refs are refused by the egress proxy; that is why claims and id reservations are branches.
- `claims-status.mjs` reads only remote evidence, so it gives the same answer everywhere.

## 4. Multiple stories in parallel

- Each session: its own worktree, branch and story. Never two sessions in one checkout.
- Stories that touch a shared contract (rule 4 in AGENTS.md) run one at a time. Others can run in parallel
  once the contract they consume is merged.
- Stacking on an unmerged dependency: `BASE=origin/claude/sc-3.1-domain-model ./scripts/agent-start.sh …`.
  Rebase onto main as soon as the dependency merges.

## 5. Merge train

Several PRs ready at once: merge one; every other open branch runs
`git fetch origin && git rebase origin/main && ./scripts/local-gate.sh` before its turn. Conflicts between
agents go to the coordinator (AGENTS.md § Merge conflicts).

## 6. After a merge (on main)

```bash
git checkout main && git pull
node scripts/backlog-board.mjs           # regenerate backlog/BOARD.md
git commit -am "chore(backlog): refresh board" && git push
```

## 7. Rollback

Revert the squash commit on main with a `revert:` PR; reopen the story (status In Progress, owner empty)
with the reason under Issues Encountered. Never rewrite main's history.

## 8. CI

`.github/workflows/ci.yml` runs `./scripts/local-gate.sh` on every PR and on main. When CI is unavailable,
a green local gate pasted in the PR is the accepted substitute, subject to the reviewer.
