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
# The CI runner (ubuntu-latest) has bash/grep/sed but no poppler or Tesseract; the container has all.
# Failing stubs placed first on PATH hide only those tools, so a test that silently needs them
# fails here too (a trimmed PATH would also hide bash/grep, which the hook tests need).
docker compose exec -T app sh -c '
  stubs="$(mktemp -d)"
  for tool in pdfinfo pdftoppm pdftocairo tesseract; do
    printf "#!/bin/sh\necho \"%s is not installed on the CI runner\" >&2\nexit 127\n" "$tool" > "$stubs/$tool"
    chmod +x "$stubs/$tool"
  done
  PATH="$stubs:$PATH" python -m pytest tests/ -v -p no:cacheprovider
'

echo ""
echo "=== All checks passed ==="
