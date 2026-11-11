#!/usr/bin/env bash
# The canonical pre-PR gate. CI runs the same steps; a green local run quoted in the PR is the
# accepted substitute when CI is degraded.
#
# Usage: ./scripts/local-gate.sh [--fast]
#   --fast   skip the slow parts (OCR-marked tests, frontend build)
#
# Steps (each skipped with a note when its part of the repo does not exist yet):
#   1. backlog-lint            story frontmatter, ids, Done evidence
#   2. backend: ruff check + ruff format --check + pytest
#   3. frontend: biome check + tsc --noEmit + vitest + vite build
#   4. secret scan of the branch diff vs origin/main
# Prints "GATE PASSED" only when every step that ran is green.

set -uo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
FAST=0
[ "${1:-}" = "--fast" ] && FAST=1
FAILED=()
step() { printf '\n── %s\n' "$1"; }
run() {
  local name=$1
  shift
  if "$@"; then echo "✓ $name"; else echo "✗ $name"; FAILED+=("$name"); fi
}

step "backlog"
run backlog-lint node scripts/backlog-lint.mjs

step "backend"
if [ -f backend/pyproject.toml ]; then
  export UV_SYSTEM_CERTS=${UV_SYSTEM_CERTS:-1}
  (cd backend && uv sync --frozen --inexact -q) || FAILED+=("uv sync")
  run ruff-check bash -c "cd backend && uv run ruff check ."
  run ruff-format bash -c "cd backend && uv run ruff format --check ."
  if [ "$FAST" = "1" ]; then
    run pytest bash -c "cd backend && uv run pytest -m 'not ocr and not docling'"
  else
    run pytest bash -c "cd backend && uv run pytest"
  fi
else
  echo "• no backend/ yet"
fi

step "frontend"
if [ -f frontend/package.json ]; then
  (cd frontend && pnpm install --frozen-lockfile --silent) || FAILED+=("pnpm install")
  run biome bash -c "cd frontend && pnpm exec biome check ."
  run tsc bash -c "cd frontend && pnpm exec tsc --noEmit -p ."
  if grep -q '"test"' frontend/package.json; then run vitest bash -c "cd frontend && pnpm test --run"; fi
  [ "$FAST" = "1" ] || run vite-build bash -c "cd frontend && pnpm build"
else
  echo "• no frontend/ yet"
fi

step "secrets"
git fetch --quiet origin main 2>/dev/null || true
HITS=$(git diff origin/main...HEAD -U0 -- . ':(exclude).githooks/*' ':(exclude)scripts/local-gate.sh' 2>/dev/null \
  | grep -E '^\+' | grep -vE '^\+\+\+' \
  | grep -nE 'sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|BEGIN[A-Z ]*PRIVATE KEY|eyJhbGciOiJ' || true)
if [ -n "$HITS" ]; then echo "✗ possible secret:"; echo "$HITS"; FAILED+=("secrets"); else echo "✓ secrets"; fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "GATE PASSED"
else
  echo "GATE FAILED: ${FAILED[*]}"
  exit 1
fi
