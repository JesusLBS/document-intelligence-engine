#!/usr/bin/env bash
# Runs what .github/workflows/tests.yml runs, inside the running app container,
# so you know before pushing whether CI will pass.
. "$(dirname "$0")/lib.sh"
set -e

if ! app_running; then
  echo "The app container is not running. Start it first: make up"
  exit 1
fi

echo "--- tests (pytest), without poppler/tesseract like CI ---"
# The CI runner (ubuntu-latest) has no poppler or Tesseract; the container does. Running with
# PATH limited to Python's bin hides them, so a test that silently needs them fails here too.
docker compose exec -T app env PATH=/usr/local/bin python -m pytest tests/ -v -p no:cacheprovider

echo ""
echo "=== All checks passed ==="
