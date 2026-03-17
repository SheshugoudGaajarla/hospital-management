#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-infra/docker/docker-compose.yml}"

docker compose -f "$COMPOSE_FILE_PATH" run --rm db-backup /bin/sh /scripts/db-backup-once.sh
