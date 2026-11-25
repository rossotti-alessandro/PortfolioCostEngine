#!/usr/bin/env bash
# Run FeeLens maintenance commands inside the container. People and roles are managed in the app
# (Team & access), not here.
#   ./feelens.sh retention --dry-run
set -euo pipefail
cd "$(dirname "$0")"
cmd=${1:?"usage: feelens.sh retention [--dry-run]"}
shift
case "$cmd" in
  retention) ;;
  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
exec docker compose exec -T feelens sh -c 'cd backend && exec .venv/bin/python -m "pce.$0" "$@"' "$cmd" "$@"
