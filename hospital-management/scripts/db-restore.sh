#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-infra/docker/docker-compose.yml}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-file.sql|backup-file.sql.gz> [--yes]"
  exit 1
fi

BACKUP_FILE="$1"
FORCE_RESTORE="${2:-}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

if [[ "$FORCE_RESTORE" != "--yes" ]]; then
  read -r -p "This will overwrite the current database. Continue? (yes/no): " answer
  if [[ "$answer" != "yes" ]]; then
    echo "Restore cancelled."
    exit 1
  fi
fi

echo "Resetting public schema..."
docker compose -f "$COMPOSE_FILE_PATH" exec -T postgres sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'

echo "Restoring from: $BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.gz ]]; then
  gzip -dc "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE_PATH" exec -T postgres sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
else
  cat "$BACKUP_FILE" | docker compose -f "$COMPOSE_FILE_PATH" exec -T postgres sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
fi

echo "Restore completed successfully."
