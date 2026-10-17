#!/usr/bin/env bash
# Runs what .github/workflows/tests.yml runs, inside the running app container,
# so you know before pushing whether CI will pass.
. "$(dirname "$0")/lib.sh"
set -e

if ! app_running; then
  echo "The app container is not running. Start it first: make up"
  exit 1
fi

echo "--- tests (pytest) ---"
docker compose exec -T app pytest tests/ -v

echo ""
echo "=== All checks passed ==="
