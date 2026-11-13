#!/usr/bin/env bash
# Restore a backup made by backup.sh. Stops FeeLens, replaces ./data, starts it again.
#   ./restore.sh feelens-20261113T020000Z.tar.age /path/to/age-private-key.txt
# Test this every quarter on a spare machine: a backup that was never restored is not a backup.
set -euo pipefail
cd "$(dirname "$0")"
file=${1:?"usage: restore.sh <backup.tar.age> <age identity file>"}
key=${2:?"usage: restore.sh <backup.tar.age> <age identity file>"}
docker compose stop feelens
old="data.before-restore-$(date -u +%Y%m%dT%H%M%SZ)"
mv data "$old"
mkdir data
age -d -i "$key" "$file" | tar -C data -xf -
mv data/backup.sqlite data/pce.sqlite
docker compose start feelens
echo "restored. Previous data kept in $old: delete it once you have checked the restore."
