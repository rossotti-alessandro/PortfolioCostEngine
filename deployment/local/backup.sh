#!/usr/bin/env bash
# Encrypted backup of the database and stored documents. Run daily (cron or Task Scheduler).
#   ./backup.sh /path/to/backup/folder
# Needs: docker, age (https://age-encryption.org, BSD-3-Clause) and BACKUP_RECIPIENT in .env.
# Keeps 30 days of backups; erased prospects disappear from backups after that, as the DPIA states.
set -euo pipefail
cd "$(dirname "$0")"
dest=${1:?"usage: backup.sh <backup folder>"}
recipient=$(grep -E '^BACKUP_RECIPIENT=' .env | cut -d= -f2-)
[ -n "$recipient" ] || { echo "set BACKUP_RECIPIENT in .env (age public key)" >&2; exit 1; }
mkdir -p "$dest"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
# Consistent copy of a live SQLite database, then documents; nothing unencrypted touches the backup folder.
docker compose exec -T feelens sh -c \
  'cd backend && .venv/bin/python -c "import sqlite3; s=sqlite3.connect(\"/app/var/pce.sqlite\"); d=sqlite3.connect(\"/app/var/backup.sqlite\"); s.backup(d); d.close()"'
mkdir -p data/storage  # empty until the first upload
out="$dest/feelens-$stamp.tar.age"
tar -C data -cf - backup.sqlite storage | age -r "$recipient" -o "$out.partial"
mv "$out.partial" "$out"  # a failed run never leaves a file that looks like a good backup
rm -f data/backup.sqlite
find "$dest" -name 'feelens-*.tar.age' -mtime +30 -delete
echo "backup written: $out"
