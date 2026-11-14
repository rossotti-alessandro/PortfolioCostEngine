# Workflow

The commands behind [AGENTS.md](../AGENTS.md). Works the same for Claude Code, Codex and Cursor, on a
laptop or in a cloud session.

## TL;DR

```bash
git fetch origin
node scripts/claims-status.mjs                             # who is LIVE on what
node scripts/backlog-board.mjs --ready                     # pick a story (or reserve one for the request)
OWNER="Fee ledger thread" AGENT_MODEL=claude-opus-5-5 SLUG=fee-ledger ./scripts/agent-start.sh claude SC-7.1
cd .claude/worktrees/claude-sc-7.1                         # cloud with a mandated branch: NO_WORKTREE=1, stay put
# … change loop, commit + push each unit, node scripts/backlog-set.mjs SC-7.1 progress=40 …
git fetch origin && git merge origin/main
# close the story file (status, Outcome, Branch & Commits), update HANDOFF/specs if needed, then:
node scripts/backlog-board.mjs && git commit -am "chore(backlog): refresh board" && git push
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
| Regression | Module suite (`uv run pytest tests/test_<area>.py`, `pnpm test --run`) | Green |
| Self-review | Read your own diff (`git diff origin/main...`) with ponytail-review and the rules for those paths | Every line is needed |
| Commit | Conventional commit, why in the body; push | Hash in the story's Branch & Commits |

## 2. Branches and commits

- Laptop: story branch `<agent>/sc-<id>-<slug>` from fresh `origin/main` (`claude/sc-7.1-fee-ledger`).
- Cloud session with a mandated branch (`claude/project-thread-*`): use it for every story of the thread,
  one PR at a time. After the squash merge, before the next story: `git fetch origin && git merge origin/main`
  and push (no force needed; the next PR's diff then holds only the new story).
- Commit subject: `<type>(<scope>): <subject>` ≤ 72 chars (the hook blocks longer). Types: feat fix
  refactor test chore docs perf deps ci build style revert. Scopes in use: `finance`, `extraction`,
  `evaluation`, `intake`, `instruments`, `api`, `db`, `ui`, `report`, `privacy`, `backlog`, `deck`,
  `infra`, `deps`, `docs`, `agents`, `rules`.
- Dependency changes get their own `deps:` PR with the licence of every new package in the description
  and Ale's approval (AGENTS.md rule 9).

## 3. Cloud sessions

- Fresh container: `./scripts/bootstrap.sh` before the full gate (Tesseract and friends), and
  `./scripts/setup-hooks.sh` once.
- Pushes to custom refs and ref deletions are refused by the egress proxy; that is why claims and id
  reservations are branches and releases are commits.
- `claims-status.mjs` reads only remote evidence, so it gives the same answer everywhere.
- Files for the person (reports, screenshots, decks) go to the shared project folder as well as the PR;
  nothing with real client data goes anywhere.

## 4. Multiple stories in parallel

- Each session: its own worktree or mandated branch, and its own story. Never two sessions in one checkout.
- Stories that touch a shared contract (rule 4 in AGENTS.md) run one at a time. Others can run in parallel
  once the contract they consume is merged.
- Stacking on an unmerged dependency: `BASE=origin/claude/sc-3.1-domain-model ./scripts/agent-start.sh …`.
  Rebase onto main as soon as the dependency merges. Say "stacked on #N" in the PR.

## 5. Merge train

Several PRs ready at once: merge one; every other open branch runs
`git fetch origin && git merge origin/main && node scripts/backlog-board.mjs && ./scripts/local-gate.sh`
before its turn. `backlog/BOARD.md` conflicts are resolved by regenerating it. Conflicts in code between
agents go to the coordinator (AGENTS.md § Merge conflicts).

## 6. Asking for approval (rule 9)

One message per PR, to Ale, that names the PR, says in one sentence what changes and why it needs approval
(finance formula, privacy, new dependency and its licence…), and gives the risk if wrong. Keep working on
other stories while waiting. Merge only after Ale's own words approve it.

## 7. Reporting

- Lead with the outcome and the link, then the numbers with their source, then what is open and who owns it.
- Numbers are measured, dated and say what they count; targets are called targets.
- After two status replies with nothing needed from the person, keep progress on the checklist instead.

## 8. Rollback

Revert the squash commit on main with a `revert:` PR; reopen the story (status In Progress, owner empty)
with the reason under Issues Encountered. Never rewrite main's history.

## 9. CI

`.github/workflows/ci.yml` runs `./scripts/local-gate.sh` on every PR and on main. When CI is unavailable,
a green local gate pasted in the PR is the accepted substitute, subject to the reviewer.
