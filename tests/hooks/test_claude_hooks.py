import json
import subprocess
import tempfile
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
REPO = "/repo"
EMPTY_DIR = Path(tempfile.mkdtemp(prefix="hook-cwd-"))


def run_hook(name: str, tool_name: str, tool_input: dict, cwd: Path = None) -> bool:
    """
    Run a Claude Code PreToolUse hook with the JSON it receives; True when it denies the call.

    Runs in an empty directory by default: the result must never depend on which files exist
    where the hook runs (a real .env in the developer's clone once hid a bug that CI caught).
    """
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input})
    result = subprocess.run(["bash", str(HOOKS / name)], input=payload, capture_output=True, text=True,
                            check=True, cwd=cwd or EMPTY_DIR)
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
        ("Bash", {"command": "cat .env*"}),
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

    @pytest.mark.parametrize("files", [[], [".env.example"], [".env", ".env.example"]])
    def test_wildcards_do_not_depend_on_the_files_where_the_hook_runs(self, tmp_path, files):
        # Regression: ".env*" was expanded as a filename glob, so it was denied only where a .env existed.
        for name in files:
            (tmp_path / name).write_text("X=1")

        assert run_hook("block-env-access.sh", "Grep", {"pattern": "KEY", "glob": ".env*"}, cwd=tmp_path)
        assert run_hook("block-env-access.sh", "Bash", {"command": "cat .env*"}, cwd=tmp_path)


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
