#!/usr/bin/env bash
# Runs what .github/workflows/tests.yml runs, inside the running app container,
# so you know before pushing whether CI will pass.
. "$(dirname "$0")/lib.sh"
set -e

if ! app_running; then
  echo "The app container is not running. Start it first: make up"
  exit 1
fi

echo "--- tests (pytest) on a clean copy, without poppler/tesseract like CI ---"
# Two things make the working copy differ from the CI checkout, and both have hidden bugs:
#  - Ignored local files (.env, storage/, uploads/): only files git would commit are copied
#    (tracked + new, not ignored) to a fresh folder, like actions/checkout does.
#  - Tools the container has and the CI runner (ubuntu-latest) does not: failing stubs placed
#    first on PATH hide poppler and Tesseract; bash/grep/sed stay available, as on the runner.
git ls-files --cached --others --exclude-standard \
  | while IFS= read -r file; do [ -e "$file" ] && printf '%s\n' "$file"; done \
  | tar -cf - -T - \
  | docker compose exec -T app sh -c '
      set -e
      workdir="$(mktemp -d)"
      tar -xf - -C "$workdir"
      stubs="$(mktemp -d)"
      for tool in pdfinfo pdftoppm pdftocairo tesseract; do
        printf "#!/bin/sh\necho \"%s is not installed on the CI runner\" >&2\nexit 127\n" "$tool" > "$stubs/$tool"
        chmod +x "$stubs/$tool"
      done
      cd "$workdir"
      status=0
      PATH="$stubs:$PATH" python -m pytest tests/ -v -p no:cacheprovider || status=$?
      rm -rf "$workdir" "$stubs"
      exit $status
    '

echo ""
echo "=== All checks passed ==="
