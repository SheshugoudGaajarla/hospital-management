#!/usr/bin/env sh
set -eu

BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"

echo "DB backup loop started. Interval: ${BACKUP_INTERVAL_SECONDS}s"

while true; do
  /bin/sh /scripts/db-backup-once.sh
  sleep "$BACKUP_INTERVAL_SECONDS"
done
