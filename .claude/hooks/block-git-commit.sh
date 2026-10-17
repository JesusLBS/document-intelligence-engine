#!/usr/bin/env bash
# PreToolUse hook (Bash): Claude must never create commits on its own.
# It suggests the message (see /sugerir-commit) and the developer commits
# manually. Plain grep on the raw hook JSON so it works without jq/python.

input="$(cat)"

if printf '%s' "$input" | grep -Eq '(^|[^[:alnum:]_-])git([[:space:]]+-[^[:space:]]+([[:space:]]+[^-[:space:]][^[:space:]]*)?)*[[:space:]]+commit([^[:alnum:]_-]|$)'; then
  cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Project rule: Claude never runs git commit. Use /sugerir-commit to review ALL modified files and suggest the Conventional Commit message; the developer commits manually."
  }
}
JSON
  exit 0
fi

exit 0
