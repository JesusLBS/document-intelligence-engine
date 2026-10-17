#!/usr/bin/env bash
# Checks local prerequisites. Read-only: installs and fixes nothing.
# One line per check (OK / MISSING / WARN) so a human or an AI can parse it at a glance.
. "$(dirname "$0")/lib.sh"

echo "=== Docker (main environment) ==="
if command -v docker >/dev/null 2>&1; then
  echo "docker: OK ($(docker --version))"
  if docker info >/dev/null 2>&1; then
    echo "docker-daemon: OK (running)"
  else
    echo "docker-daemon: MISSING (installed but not running: open Docker Desktop)"
  fi
else
  echo "docker: MISSING (install Docker Desktop)"
fi

if docker compose version >/dev/null 2>&1; then
  echo "docker-compose: OK ($(docker compose version --short))"
else
  echo "docker-compose: MISSING"
fi

echo "=== Project ==="
if [ -f .env ]; then
  echo "env-file: OK"
else
  echo "env-file: MISSING (cp .env.example .env)"
fi

if grep -Eq "^[[:space:]]*127\.0\.0\.1[[:space:]]+([^#]*[[:space:]])?$APP_HOST([[:space:]]|$)" /etc/hosts 2>/dev/null; then
  echo "hosts: OK ($APP_HOST -> 127.0.0.1)"
else
  echo "hosts: MISSING (add to /etc/hosts: 127.0.0.1 $APP_HOST)"
fi

# macOS sends *.test to the resolver in /etc/resolver/test first (Laravel Herd's dnsmasq).
# If that DNS is not running, every request waits ~5s before falling back to /etc/hosts.
LOOKUP="$(curl -s -o /dev/null -w '%{time_namelookup}' --max-time 10 "$APP_URL/" 2>/dev/null)"
if [ -n "$LOOKUP" ] && awk "BEGIN {exit !($LOOKUP > 1)}"; then
  if [ -f /etc/resolver/test ]; then
    echo "dns: WARN (resolving $APP_HOST takes ${LOOKUP}s: /etc/resolver/test points to a DNS that is not answering, usually Laravel Herd stopped)"
  else
    echo "dns: WARN (resolving $APP_HOST takes ${LOOKUP}s)"
  fi
else
  echo "dns: OK"
fi

if [ -n "$(docker compose port web 80 2>/dev/null)" ]; then
  echo "port-80: OK (used by this project's nginx)"
elif lsof -nP -iTCP:80 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port-80: WARN (taken by another process, usually another project left running: lsof -nP -iTCP:80 -sTCP:LISTEN)"
else
  echo "port-80: OK (free)"
fi

if [ "$(git config core.hooksPath 2>/dev/null)" = ".githooks" ]; then
  echo "git-hooks: OK (.githooks active)"
else
  echo "git-hooks: WARN (pre-push not active: git config core.hooksPath .githooks)"
fi

echo "=== Local venv (optional, only if you run without Docker) ==="
if command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12: OK"
else
  echo "python3.12: MISSING (optional: brew install python@3.12)"
fi

if command -v tesseract >/dev/null 2>&1; then
  if tesseract --list-langs 2>/dev/null | grep -qx spa; then
    echo "tesseract-spa: OK"
  else
    echo "tesseract-spa: MISSING (optional: brew install tesseract-lang)"
  fi
else
  echo "tesseract: MISSING (optional: brew install tesseract tesseract-lang)"
fi

if command -v pdftoppm >/dev/null 2>&1; then
  echo "poppler: OK"
else
  echo "poppler: MISSING (optional: brew install poppler)"
fi
