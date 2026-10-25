import json
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
REPO = "/repo"


def run_hook(name: str, tool_name: str, tool_input: dict) -> bool:
    """Run a Claude Code PreToolUse hook with the JSON it receives; True when it denies the call."""
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(["bash", str(HOOKS / name)], input=payload, capture_output=True, text=True, check=True)
    return '"permissionDecision": "deny"' in result.stdout


class TestBlockEnvAccess:
    """.env files (API keys) are never read, edited or searched; .env.example and docs about .env are fine."""

    @pytest.mark.parametrize("tool_name, tool_input", [
        ("Read", {"file_path": f"{REPO}/.env"}),
        ("Read", {"file_path": f"{REPO}/.env.local"}),
        ("Edit", {"file_path": f"{REPO}/.env", "old_string": "a", "new_string": "b"}),
        ("Write", {"file_path": f"{REPO}/.env.production", "content": "X=1"}),
        ("Grep", {"pattern": "KEY", "path": f"{REPO}/.env"}),
        ("Grep", {"pattern": "KEY", "glob": ".env*"}),
        ("Glob", {"pattern": "**/.env"}),
        ("Bash", {"command": "cat .env"}),
        ("Bash", {"command": "grep KEY .env | head"}),
        ("Bash", {"command": "source ./.env.local"}),
        ("Bash", {"command": "python3 -c 'print(open(\".env\").read())'"}),
    ])
    def test_env_files_are_denied(self, tool_name, tool_input):
        assert run_hook("block-env-access.sh", tool_name, tool_input)

    @pytest.mark.parametrize("tool_name, tool_input", [
        ("Read", {"file_path": f"{REPO}/.env.example"}),
        ("Read", {"file_path": f"{REPO}/app/config/__init__.py"}),
        ("Edit", {"file_path": f"{REPO}/README.md", "old_string": "edit .env and", "new_string": "cat .env"}),
        ("Grep", {"pattern": "\\.env", "path": f"{REPO}/app"}),
        ("Glob", {"pattern": "**/*.py"}),
        ("Bash", {"command": "cat .env.example"}),
        ("Bash", {"command": "make up", "description": "Recreate the container to reload env vars"}),
        ("Bash", {"command": "printf 'after editing `.env` run make up' > notes.md"}),
    ])
    def test_everything_else_is_allowed(self, tool_name, tool_input):
        assert not run_hook("block-env-access.sh", tool_name, tool_input)


# Built from parts so this file itself never contains the literal command the hook looks for.
GIT_COMMIT = "git " + "commit"


class TestBlockGitCommit:
    """Claude never commits: the developer does, after /sugerir-commit."""

    @pytest.mark.parametrize("command", [
        f"{GIT_COMMIT} -m 'x'",
        f"git -C repo {GIT_COMMIT.split()[1]}",
        f"cd x && {GIT_COMMIT} --amend",
    ])
    def test_commits_are_denied(self, command):
        assert run_hook("block-git-commit.sh", "Bash", {"command": command})

    @pytest.mark.parametrize("command", ["git status", "git log --oneline", "git diff --cached"])
    def test_other_git_commands_are_allowed(self, command):
        assert not run_hook("block-git-commit.sh", "Bash", {"command": command})
