#!/usr/bin/env bash
# Claim a backlog story atomically, then create an isolated worktree + branch for it.
#
# Usage:   [OWNER=..] [AGENT_MODEL=..] [SLUG=..] [BASE=..] [NO_WORKTREE=1] ./scripts/agent-start.sh <agent> <story-id>
# Example: OWNER="Build demo thread" AGENT_MODEL=claude-opus-5-5 SLUG=fee-ledger \
#            ./scripts/agent-start.sh claude SC-7.1
#
# The claim is a remote BRANCH `claims/sc-<id>` holding one empty commit whose message records
# owner, model, agent, host and time. Creating a branch that already exists is rejected by the
# server (non-fast-forward), so two sessions racing for the same story cannot both win. Branches,
# not a custom ref namespace, because the cloud egress proxy refuses non-branch refs.
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
ISO_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BASE_SHA=$(git rev-parse "${BASE:-origin/main}")
MSG="claim SC-${ID} owner=${OWNER:-$AGENT} model=${AGENT_MODEL:-unknown} agent=${AGENT}@$(hostname -s 2>/dev/null || echo host) at=${ISO_TS}"
CLAIM_COMMIT=$(git commit-tree "${BASE_SHA}^{tree}" -p "$BASE_SHA" -m "$MSG")
CLAIM_TTL_HOURS="${CLAIM_TTL_HOURS:-48}"

if git push --quiet origin "${CLAIM_COMMIT}:refs/heads/${CLAIM_BRANCH}" 2>/dev/null; then
  echo "✓ Claimed SC-${ID} (origin/${CLAIM_BRANCH})"
else
  EXISTING=$(git ls-remote origin "refs/heads/${CLAIM_BRANCH}" | awk '{print $1}')
  if [ -z "$EXISTING" ]; then
    echo "✗ Push of ${CLAIM_BRANCH} failed and no claim exists: check your push access." >&2
    exit 1
  fi
  git fetch --quiet origin "refs/heads/${CLAIM_BRANCH}" 2>/dev/null || true
  echo "✗ SC-${ID} is already claimed: $(git log -1 --format='%s (%cr)' "$EXISTING" 2>/dev/null || echo "$EXISTING")" >&2
  echo "  Stale (> ${CLAIM_TTL_HOURS}h, no branch activity)? Ask the coordinator to release it. Never steal a claim." >&2
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
    git push --quiet origin --delete "$CLAIM_BRANCH" 2>/dev/null || true
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
git -C "$WTPATH" push -q -u origin "$BRANCH" 2>/dev/null || echo "⚠ Could not push ${BRANCH} yet; push it before writing code."

cat <<EOF

Story SC-${ID} claimed.
  Worktree : ${WTPATH}
  Branch   : ${BRANCH}
  Claim    : origin/${CLAIM_BRANCH}
Next: read the story, declare owned paths under ## Implementation Notes, then work in ${WTPATH}.
End with: ./scripts/agent-teardown.sh --yes ${WTPATH}
EOF
