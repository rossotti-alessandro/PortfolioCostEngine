#!/usr/bin/env bash
# Activate the committed git hooks for this clone (and every worktree made from it).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh
echo "✓ git hooks active (.githooks/)"
