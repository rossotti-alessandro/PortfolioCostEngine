#!/usr/bin/env bash
# End a story session: push, release the claim branch, hand back ownership if unfinished,
# remove the worktree, delete the story branch only if it is merged.
#
# Usage:   ./scripts/agent-teardown.sh [--yes] <worktree-path | story-id>
#   --yes  non-interactive (required for agents); the worktree must be clean.
# Passing a story id (SC-7.1) instead of a path releases the claim of a NO_WORKTREE session.

set -euo pipefail

YES=0
if [ "${1:-}" = "--yes" ] || [ "${1:-}" = "-y" ]; then YES=1; shift; fi
TARGET=${1:?"Usage: agent-teardown.sh [--yes] <worktree-path | story-id>"}
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

if [ -d "$TARGET" ]; then
  WTPATH="$TARGET"
  BRANCH=$(git -C "$WTPATH" branch --show-current)
  ID=$(printf '%s' "$BRANCH" | sed -nE 's#^[^/]+/sc-([0-9]+(\.[0-9]+)*)-.*#\1#p')
else
  WTPATH="$ROOT"
  BRANCH=$(git branch --show-current)
  ID=$(printf '%s' "$TARGET" | sed -E 's/^[sS][cC]-//')
fi
[ -n "$ID" ] || { echo "✗ Cannot derive the story id from '${TARGET}'." >&2; exit 1; }

if [ -n "$(git -C "$WTPATH" status --porcelain)" ]; then
  echo "✗ Uncommitted changes in ${WTPATH}. Commit them first." >&2
  git -C "$WTPATH" status --short >&2
  exit 1
fi
if [ "$YES" -ne 1 ]; then
  if [ ! -t 0 ]; then echo "✗ Non-interactive: pass --yes." >&2; exit 1; fi
  read -r -p "Push ${BRANCH}, release SC-${ID}, remove worktree? [y/N] " ok
  [ "$ok" = "y" ] || { echo "Aborted."; exit 1; }
fi

git -C "$WTPATH" push -q -u origin "$BRANCH" 2>/dev/null || echo "(nothing to push)"

# Hand back ownership when the story is unfinished, so the board shows it as unowned.
TASK_FILE=$(ls "$WTPATH/backlog/tasks/" | grep -iE "^sc-${ID//./\\.} " | head -1 || true)
if [ -n "$TASK_FILE" ] && grep -qE '^status: *"?In Progress"?' "$WTPATH/backlog/tasks/$TASK_FILE"; then
  node "$WTPATH/scripts/backlog-set.mjs" "SC-${ID}" owner="" model="" >/dev/null
  git -C "$WTPATH" commit -qam "chore(backlog): release sc-${ID} owner (session ended)"
  git -C "$WTPATH" push -q origin "$BRANCH" 2>/dev/null || true
  echo "✓ Cleared owner on SC-${ID} (still In Progress)"
fi

if git push --quiet origin --delete "claims/sc-${ID}" 2>/dev/null; then
  echo "✓ Released claim claims/sc-${ID}"
else
  echo "(no claim branch to release for SC-${ID})"
fi

if [ "$WTPATH" != "$ROOT" ]; then
  git worktree remove "$WTPATH"
  git worktree prune
  git fetch --quiet origin
  # Squash merges leave the branch a non-ancestor of main; only the ancestor case is detectable offline.
  if git merge-base --is-ancestor "$BRANCH" origin/main 2>/dev/null; then
    git branch -d "$BRANCH" && git push --quiet origin --delete "$BRANCH" 2>/dev/null || true
    echo "✓ Deleted merged branch ${BRANCH}"
  else
    echo "• Kept ${BRANCH} (not an ancestor of origin/main). Delete it after the PR merges."
  fi
fi
echo "✓ Session ended."
