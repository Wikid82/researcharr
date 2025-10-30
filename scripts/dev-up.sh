#!/usr/bin/env bash
set -euo pipefail

# Developer helper: run compose in watch mode (rebuilds and refreshes on file changes)
COMPOSE_FILE="docker-compose.feat.yml"

echo "Starting development stack with file-watch enabled (compose file: ${COMPOSE_FILE})"
exec docker compose -f "${COMPOSE_FILE}" up --build --watch "$@"
