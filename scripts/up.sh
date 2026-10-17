#!/usr/bin/env bash
# Starts the stack in the background and waits until the API is healthy.
# Pass --build to rebuild the image (needed only when requirements.txt or the Dockerfile change).
. "$(dirname "$0")/lib.sh"
set -e

if [ ! -f .env ]; then
  echo "Missing .env. Create it first: cp .env.example .env"
  exit 1
fi

docker compose up -d --wait "$@"

echo ""
echo "API ready: $APP_URL/api/v1/health"
echo "Logs: make logs · Stop: make down"
