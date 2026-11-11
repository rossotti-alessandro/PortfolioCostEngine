# shellcheck shell=bash
# Shared helpers for the repo's committed git hooks (.githooks/).
# Sourced by pre-commit / commit-msg / pre-push. Not executed directly.
#
# Enforcement model:
#   HOOKS_ENFORCE=1 (default) → a check failure blocks the git operation.
#   HOOKS_ENFORCE=0           → checks print warnings but never block.
# The secret scan ALWAYS blocks regardless of HOOKS_ENFORCE — leaking a key
# is never acceptable.
#
# These hooks run under every tool (Claude Code, Cursor, Codex, plain git)
# because they live in the repo and are wired via `core.hooksPath .githooks`.

set -uo pipefail

HOOKS_ENFORCE="${HOOKS_ENFORCE:-1}"

# Resolve repo root for the worktree the hook fired in.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- output helpers --------------------------------------------------------
if [ -t 2 ]; then
  _C_RED=$'\033[31m'; _C_YEL=$'\033[33m'; _C_GRN=$'\033[32m'; _C_DIM=$'\033[2m'; _C_OFF=$'\033[0m'
else
  _C_RED=''; _C_YEL=''; _C_GRN=''; _C_DIM=''; _C_OFF=''
fi

hook_info()  { printf '%s\n' "${_C_DIM}[hook] $*${_C_OFF}" >&2; }
hook_ok()    { printf '%s\n' "${_C_GRN}[hook] $*${_C_OFF}" >&2; }
hook_warn()  { printf '%s\n' "${_C_YEL}[hook] WARN: $*${_C_OFF}" >&2; }
hook_error() { printf '%s\n' "${_C_RED}[hook] FAIL: $*${_C_OFF}" >&2; }

# fail <message> — block when enforcing, warn when HOOKS_ENFORCE=0.
# Sets HOOK_FAILED=1 so the caller can exit non-zero after running all checks.
HOOK_FAILED=0
fail() {
  if [ "$HOOKS_ENFORCE" = "1" ]; then
    hook_error "$1"
    HOOK_FAILED=1
  else
    hook_warn "$1 ${_C_DIM}(warn-only: HOOKS_ENFORCE=0)${_C_OFF}"
  fi
}

# hard_fail <message> — always blocks, ignores HOOKS_ENFORCE (security checks).
hard_fail() {
  hook_error "$1"
  HOOK_FAILED=1
}

# finish — exit 1 if any check failed, else 0.
finish() {
  if [ "$HOOK_FAILED" = "1" ]; then
    hook_error "commit/push blocked. Fix the above, or set HOOKS_ENFORCE=0 to bypass non-security checks."
    exit 1
  fi
  exit 0
}
