#!/usr/bin/env bash
# Run FeeLens maintenance commands inside the container.
#   ./feelens.sh users create ale --tenant safe-capital --role senior --role analyst --admin
#   ./feelens.sh users list --tenant safe-capital
#   ./feelens.sh retention --dry-run
set -euo pipefail
cd "$(dirname "$0")"
cmd=${1:?"usage: feelens.sh users|retention ..."}
shift
case "$cmd" in
  users | retention) ;;
  *) echo "unknown command: $cmd" >&2; exit 2 ;;
esac
exec docker compose exec -T feelens sh -c 'cd backend && exec .venv/bin/python -m "pce.$0" "$@"' "$cmd" "$@"
