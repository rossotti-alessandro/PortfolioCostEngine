#!/usr/bin/env bash
# Claim a backlog story atomically, then create an isolated worktree + branch for it.
#
# Usage:   [OWNER=..] [AGENT_MODEL=..] [SLUG=..] [BASE=..] [NO_WORKTREE=1] ./scripts/agent-start.sh <agent> <story-id>
# Example: OWNER="Build demo thread" AGENT_MODEL=claude-opus-5-5 SLUG=fee-ledger \
#            ./scripts/agent-start.sh claude SC-7.1
#
# The claim is a remote BRANCH `claims/sc-<id>` whose tip is an empty commit "claim SC-<id> owner=…
# model=… agent=… at=…". Pushes are fast-forward only, so two sessions racing for the same story
# cannot both win. Branches, not custom refs, because the cloud egress proxy refuses non-branch refs.
#
# Then: worktree `.claude/worktrees/<agent>-sc-<id>` on branch `<agent>/sc-<id>-<slug>` from BASE
# (default origin/main), story frontmatter set to In Progress with owner/model/branch, committed.
# NO_WORKTREE=1 (cloud sessions with a mandated branch): claim + frontmatter only, on the current branch.
# Release with ./scripts/agent-teardown.sh.

set -euo pipefail

AGENT=${1:?"Usage: agent-start.sh <agent> <story-id>   (e.g. claude SC-7.1)"}
RAW_ID=${2:?"Usage: agent-start.sh <agent> <story-id>   (e.g. claude SC-7.1)"}
ID=$(printf '%s' "$RAW_ID" | sed -E 's/^[sS][cC]-//')
SLUG=$(printf '%s' "${SLUG:-work}" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9.-')
BRANCH="${AGENT}/sc-${ID}-${SLUG}"
CLAIM_BRANCH="claims/sc-${ID}"
WTPATH=".claude/worktrees/${AGENT}-sc-${ID}"
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

TASK_FILE=$(ls backlog/tasks/ | grep -iE "^sc-${ID//./\\.} " | head -1 || true)
if [ -z "$TASK_FILE" ]; then
  echo "✗ No backlog file for SC-${ID}. Create it first (node scripts/backlog-new-id.mjs)." >&2
  exit 1
fi
if ! grep -qE '^status: *"?To Do"?' "backlog/tasks/$TASK_FILE"; then
  echo "⚠ SC-${ID} status is not 'To Do' on this checkout. Check node scripts/claims-status.mjs before going on." >&2
fi

git fetch origin --quiet --prune

# --- Atomic claim ----------------------------------------------------------
# Free  = no claim branch, or its tip commit subject starts with "release".
# Claim = push a commit "claim ..." whose parent is the current tip (or a new branch).
# Two sessions racing from the same tip: the server accepts the first fast-forward and rejects
# the second as non-fast-forward. Release is a "release ..." commit, not a branch delete,
# because cloud egress proxies refuse ref deletion.
ISO_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
MSG="claim SC-${ID} owner=${OWNER:-$AGENT} model=${AGENT_MODEL:-unknown} agent=${AGENT}@$(hostname -s 2>/dev/null || echo host) at=${ISO_TS}"
TIP=$(git ls-remote origin "refs/heads/${CLAIM_BRANCH}" | awk '{print $1}')
if [ -n "$TIP" ]; then
  git fetch --quiet origin "refs/heads/${CLAIM_BRANCH}"
  SUBJECT=$(git log -1 --format=%s "$TIP")
  case "$SUBJECT" in
    release*) PARENT="$TIP" ;;
    *)
      echo "✗ SC-${ID} is already claimed: ${SUBJECT} ($(git log -1 --format=%cr "$TIP"))" >&2
      echo "  Stale (> ${CLAIM_TTL_HOURS:-48}h, no branch activity)? Ask the coordinator to release it. Never steal a claim." >&2
      exit 1
      ;;
  esac
else
  PARENT=$(git rev-parse origin/main)
fi
CLAIM_COMMIT=$(git commit-tree "${PARENT}^{tree}" -p "$PARENT" -m "$MSG")
if git push --quiet origin "${CLAIM_COMMIT}:refs/heads/${CLAIM_BRANCH}" 2>/dev/null; then
  echo "✓ Claimed SC-${ID} (origin/${CLAIM_BRANCH})"
else
  echo "✗ Lost the race for SC-${ID} (or no push access). Run node scripts/claims-status.mjs and pick another story." >&2
  exit 1
fi

# --- Worktree --------------------------------------------------------------
if [ "${NO_WORKTREE:-0}" = "1" ]; then
  WTPATH="$ROOT"
  BRANCH=$(git branch --show-current)
  echo "• NO_WORKTREE=1: working on current branch ${BRANCH}"
else
  mkdir -p .claude/worktrees
  if ! git worktree add "$WTPATH" -b "$BRANCH" "${BASE:-origin/main}"; then
    echo "✗ Worktree creation failed. Releasing claim." >&2
    REL=$(git commit-tree "${CLAIM_COMMIT}^{tree}" -p "$CLAIM_COMMIT" -m "release SC-${ID} (worktree creation failed)")
    git push --quiet origin "${REL}:refs/heads/${CLAIM_BRANCH}" 2>/dev/null || true
    exit 1
  fi
  for envf in .env backend/.env frontend/.env.local; do
    if [ -f "$envf" ]; then cp "$envf" "$WTPATH/$envf" && echo "✓ Copied $envf"; fi
  done
fi
git -C "$WTPATH" config core.hooksPath .githooks 2>/dev/null || true

# --- Story frontmatter -------------------------------------------------------
node "$WTPATH/scripts/backlog-set.mjs" "SC-${ID}" status="In Progress" \
  owner="${OWNER:-$AGENT}" model="${AGENT_MODEL:-unknown}" branch="$BRANCH" progress=5
git -C "$WTPATH" add "backlog/tasks/$TASK_FILE"
git -C "$WTPATH" commit -q -m "chore(backlog): claim sc-${ID}" -m "owner: ${OWNER:-$AGENT} · model: ${AGENT_MODEL:-unknown} · branch: ${BRANCH}"
git -C "$WTPATH" push -q -u origin "$BRANCH" || echo "⚠ Could not push ${BRANCH} yet; push it before writing code (the branch is part of the claim evidence)."

cat <<EOF

Story SC-${ID} claimed.
  Worktree : ${WTPATH}
  Branch   : ${BRANCH}
  Claim    : origin/${CLAIM_BRANCH}
Next: read the story, declare owned paths under ## Implementation Notes, then work in ${WTPATH}.
End with: ./scripts/agent-teardown.sh --yes ${WTPATH}
EOF
