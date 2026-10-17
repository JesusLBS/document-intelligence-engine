#!/usr/bin/env bash
# Shared helpers for scripts/*.sh. Sourced, not executed.

# Run from the repo root no matter where the script was called from.
cd "$(dirname "$0")/.." || exit 1

# Local domain served by nginx on port 80 (server_name in nginx/default.conf, entry in /etc/hosts).
APP_HOST="document-intelligence.test"
APP_URL="http://$APP_HOST"

# True when the app container is running.
app_running() {
  [ -n "$(docker compose ps --status running -q app 2>/dev/null)" ]
}
