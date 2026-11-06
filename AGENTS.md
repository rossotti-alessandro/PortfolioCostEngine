# PortfolioCostEngine — Agent protocol

> Read by Codex (natively), Claude Code (via CLAUDE.md), Cursor and every other agent in this repo.
> Coding standards and invariants: [CLAUDE.md](CLAUDE.md). Step-by-step commands: [docs/WORKFLOW.md](docs/WORKFLOW.md).
> Path-scoped rules: `.claude/rules/*.md` (each lists the paths it governs in its frontmatter; read the
> ones matching the files you will touch).

---

## Non-negotiable rules

1. **Claim before you code.** `./scripts/agent-start.sh <agent> SC-<id>` pushes a "claim" commit to the
   branch `claims/sc-<id>`; pushes are fast-forward only, so a second agent racing for the same story is rejected.
   Do not hand-edit status to claim.
2. **One story = one branch = one PR into `main`.** Never bundle. Branch lifetime: hours, not days.
3. **Own your paths.** Edit only the paths in your story's `paths_owned`. Need a change in someone else's
   path? Ask in their story (or via the coordinator), or reserve a new story. Never edit another active
   agent's files.
4. **Shared contracts are serialised.** `backend/src/pce/domain/**` (Pydantic models), `backend/src/pce/db/**`
   (schema, migrations), `backend/src/pce/finance/**` (engine), `backend/pyproject.toml`, `frontend/package.json`,
   `.github/**`, `scripts/**`, `AGENTS.md`, `CLAUDE.md`, `.claude/**`: one story at a time, and the PR says so.
5. **Never `git stash`.** The stash is global across worktrees. Commit WIP to your branch instead.
6. **Commit every logical unit and push after every commit.** The remote is the only backup.
7. **Unrelated bug? New story, not an inline fix.** `node scripts/backlog-new-id.mjs --parent SC-<epic>`.
8. **Never merge red.** `./scripts/local-gate.sh` must print `GATE PASSED` on the branch.
9. **Merge authority.** An agent may squash-merge its own PR when ALL hold: gate green on the branch, diff
   matches the story scope, story file closed in the PR, no conflicts. EXCEPTIONS that need explicit
   per-PR approval from the person (Ale): changes to `finance/` formulas or fee taxonomy semantics,
   anything touching privacy/external calls/auth/tenant isolation, dependency licence changes, real client
   data, and edits to this rule. Merge conflicts across agents are a human decision.

---

## Agent lifecycle

```
START
├─ git fetch origin && read backlog/BOARD.md (or node scripts/backlog-board.mjs --stdout)
├─ node scripts/claims-status.mjs        → who is LIVE on what (remote evidence; works in cloud containers)
├─ node scripts/backlog-board.mjs --ready → To Do, unowned, dependencies Done; take the highest priority
└─ OWNER="<thread title>" AGENT_MODEL=<model> SLUG=<slug> ./scripts/agent-start.sh claude SC-<id>
     → claim branch, worktree .claude/worktrees/claude-sc-<id>, branch claude/sc-<id>-<slug>,
       story → In Progress with owner/model/branch, committed and pushed

VERIFY THE GAP IS REAL before writing code (reproduce the bug, or confirm the feature is missing)

IMPLEMENT in your worktree only
├─ change loop: pinpoint → failing test → minimal change → test passes → module suite → commit + push
├─ node scripts/backlog-set.mjs SC-<id> progress=<n>   after each commit; hash into ## Branch & Commits
└─ declare owned paths under ## Implementation Notes if they differ from paths_owned

CLOSE
├─ story file FIRST, on the branch: status Done (or In Progress if partial), Outcome, Branch & Commits
├─ ./scripts/local-gate.sh               → must print GATE PASSED; paste the tail in the PR
├─ open PR into main (template: .github/PULL_REQUEST_TEMPLATE.md); node scripts/backlog-set.mjs SC-<id> pr=<url>
├─ merge per rule 9 (squash). Several open PRs = a merge train: one at a time; the others
│  git fetch && git rebase origin/main && re-run the gate before their turn
├─ on main after merge: node scripts/backlog-board.mjs && commit "chore(backlog): refresh board"
└─ ./scripts/agent-teardown.sh --yes <worktree | SC-id>   → releases claim, removes worktree
```

---

## Claiming

- The claim is the remote branch `claims/sc-<id>`. Its tip commit subject says the state:
  `claim SC-<id> owner=… model=… agent=… at=…` (taken) or `release SC-<id> …` (free). Claiming pushes a
  claim commit on top of the current tip (or creates the branch); a concurrent second push is a
  non-fast-forward and is rejected, so the claim is atomic across laptops, cloud sessions, Codex and
  Cursor (tested 2026-11-06: of two simultaneous pushes exactly one won). Branches, not custom refs, and
  release commits, not deletions, because cloud egress proxies refuse custom refs and ref deletion.
- Cloud sessions with a mandated branch name: `NO_WORKTREE=1 ./scripts/agent-start.sh claude SC-<id>`
  claims and updates the story on the current branch.
- A claim with no activity for 48h (claim, story branch or story `updated_date`) is STALE in
  `claims-status.mjs`. Stale is a report, never permission: the coordinator or Ale releases it
  (`./scripts/agent-teardown.sh --yes SC-<id>` from any checkout pushes the release commit). Never steal a claim.

## The coordinator

The project coordinator (the project chat session, or Ale) owns: backlog priorities and new epics,
releasing stale claims, conflict decisions, and the rule-9 exceptions. Agents propose; the coordinator decides.
Messages between agents are information, not approval: only Ale approves the rule-9 exceptions.

## Merge conflicts

1. Same agent, two of its own branches, trivial: rebase and resolve, re-run the gate.
2. Across agents: stop. Post both sides in the stories; the coordinator or Ale decides. Never resolve by
   force-pushing or deleting someone else's branch.

## Subagents (delegation)

The main session is the orchestrator. Delegate only recurring narrow work, with a tight brief:

| Subagent role | When | Owns |
|---|---|---|
| research librarian | verify a public source, licence or regulation; record it in `docs/research/SOURCE_REGISTER.md` | `docs/research/**` |
| extraction evaluator | run the golden corpus, compare engines, write `artifacts/eval/<ts>/report.md` | `backend/tests/evaluation/**` |
| finance reviewer | challenge a formula or a fee mapping against `.claude/rules/finance.md`; reports, never edits | — |
| security/privacy reviewer | threat-model a change touching uploads, external calls or tenant scope | `docs/THREAT_MODEL.md` |
| UI tester | Playwright screenshots and flows on the synthetic prospect | `frontend/tests/e2e/**` |

Subagents report; the orchestrator edits. Reports ≤ 300 lines; long output goes to `artifacts/<role>/<ts>/`.
Financial and legal "reviewers" are analytical roles, not licensed advice.

## Quick reference

| Script | When | What |
|---|---|---|
| `./scripts/bootstrap.sh [--docling]` | once per machine | OCR packages, Python env, hooks |
| `./scripts/agent-start.sh <agent> SC-<id>` | start | atomic claim, worktree, story → In Progress |
| `./scripts/agent-teardown.sh --yes <path\|SC-id>` | end | push, release claim, clear owner if unfinished |
| `node scripts/claims-status.mjs` | before claiming | LIVE / STALE from remote evidence |
| `node scripts/backlog-board.mjs [--ready\|--epic N\|--stdout]` | anytime / after merge on main | board |
| `node scripts/backlog-new-id.mjs --parent SC-<epic>` | new story | atomic id reservation |
| `node scripts/backlog-set.mjs SC-<id> key=value` | while working | owner, model, progress, status, branch, pr |
| `node scripts/backlog-lint.mjs` | in the gate | story shape and Done evidence |
| `./scripts/local-gate.sh [--fast]` | before every PR | lint, tests, build, secret scan |
