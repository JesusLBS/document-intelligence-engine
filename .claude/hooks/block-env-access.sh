#!/usr/bin/env bash
# PreToolUse hook (Read, Edit, Write, Grep, Glob, Bash): Claude must never read or touch .env files
# (API keys). .env.example is allowed: it is the documented template without secrets.
# Plain grep/sed on the raw hook JSON so it works without jq/python, like block-git-commit.sh.

input="$(cat)"

# Values are split into words below; never expand them as filename globs. Without this, ".env*"
# expanded to the files in the current directory: it was denied only where a real .env existed
# (the developer's clone) and allowed in CI, where there is none.
set -f

deny() {
  cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Project rule (AGENTS.md rule 7): .env files hold API keys and are never read, edited or searched. Use .env.example for variable names, Config (app/config/__init__.py) for defaults, and the request logs (model=...) to see what the app runs with."
  }
}
JSON
  exit 0
}

# True for an env file name (.env, .env.local, .env.production...) that is not .env.example.
is_env_name() {
  case "$1" in
    .env.example) return 1 ;;
    .env|.env.*|.env\*) return 0 ;;
    *) return 1 ;;
  esac
}

# File tools: check the path fields only (file content and patterns may mention .env freely).
for field in file_path path glob; do
  for value in $(printf '%s' "$input" | grep -o "\"$field\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed 's/.*:[[:space:]]*"\(.*\)"/\1/'); do
    is_env_name "$(basename "$value")" && deny
  done
done

# Glob: a pattern that targets env files (".env*", "**/.env").
glob_pattern="$(printf '%s' "$input" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"Glob"' >/dev/null \
  && printf '%s' "$input" | grep -o '"pattern"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*:[[:space:]]*"\(.*\)"/\1/')"
case "$(basename "${glob_pattern:-x}")" in
  .env|.env\*|.env.\*) deny ;;
esac

# Bash: .env used as a path argument (cat .env, cat .env*, source .env, < .env, ./.env.local, open(".env")).
# Quotes arrive JSON-escaped (\"), so the backslash also counts as a delimiter.
# Backticked mentions in text written by heredocs (`.env`) are not path arguments.
if printf '%s' "$input" | grep -q '"tool_name"[[:space:]]*:[[:space:]]*"Bash"'; then
  for token in $(printf '%s' "$input" | grep -oE '(^|[[:space:]=<>/(\\"'"'"'])\.env(\.[A-Za-z0-9_-]+)?([[:space:];|&)>*\\"'"'"']|$)' \
                 | grep -oE '\.env(\.[A-Za-z0-9_-]+)?'); do
    is_env_name "$token" && deny
  done
fi

exit 0
