# AI-assisted development: how this project is built

> Versión en español: [AI_WORKFLOW.md](./AI_WORKFLOW.md)

This project is developed with **Claude Code as the coding agent**. The AI writes most of the code, tests and documentation; the developer defines the architecture and scope, reviews every change, verifies with real documents and is the only one who commits. This document explains the rules, the technical guardrails and the workflow that make that reliable, with links to the files that implement them.

The core idea: **nothing relies on the model "behaving"**. What matters is enforced by code (hooks, tests, CI), and what cannot be enforced is verified.

---

## 1. Context: a single source of truth

| Piece | File | Purpose |
|---|---|---|
| Rules and way of working, for **any** AI | [`AGENTS.md`](../AGENTS.md) | Single source. Codex, Cursor, Copilot and others read it directly |
| Per-tool adapters | [`CLAUDE.md`](../CLAUDE.md), [`GEMINI.md`](../GEMINI.md) | Only import `AGENTS.md` and add what is exclusive to their tool. They never copy rules, which would drift |
| Status (current phase, what works, bugs) | [`docs/project/STATUS.md`](./project/STATUS.md) | The only place status is asserted |
| Architecture, decisions and scope | [`docs/project/PROJECT_PLAN.md`](./project/PROJECT_PLAN.md) | The *why*; never marks progress |
| Hard-to-reverse decisions | [`docs/decisions/`](./decisions/README.md) (ADR) | Written and approved **before** the code: options, decision, consequences. Example: [ADR 0001](./decisions/0001-business-validation-rules.md), who validates a document (the AI or the app) |

Keeping status apart from the plan avoids the most common failure in AI-assisted projects: documents saying "in progress" about something already done, or "done" about something never built.

## 2. Technical guardrails (not just instructions)

| Rule | Mechanism | File | Tested in |
|---|---|---|---|
| The AI never commits | `PreToolUse` hook + `deny` permission | [`.claude/hooks/block-git-commit.sh`](../.claude/hooks/block-git-commit.sh), [`.claude/settings.json`](../.claude/settings.json) | [`tests/hooks/`](../tests/hooks/test_claude_hooks.py) |
| The AI never reads, edits or searches `.env` (API keys) | `PreToolUse` hook on Read, Edit, Write, Grep, Glob and Bash; `.env.example` allowed | [`.claude/hooks/block-env-access.sh`](../.claude/hooks/block-env-access.sh) | [`tests/hooks/`](../tests/hooks/test_claude_hooks.py) |
| Nobody pushes straight to `main` / `develop` | git `pre-push` hook | [`.githooks/pre-push`](../.githooks/pre-push) | — |
| Nothing merges with failing tests | GitHub Actions on every PR | [`.github/workflows/tests.yml`](../.github/workflows/tests.yml) | — |
| "Works on my machine" is not enough | `make verify` reproduces CI: it runs on a clean copy holding only the files that would be committed (no `.env`, no ignored files), with poppler and tesseract hidden | [`scripts/verify.sh`](../scripts/verify.sh) | — |

Claude Code guardrails only apply inside Claude Code. For other AIs, `AGENTS.md` states explicitly that those rules depend on them ([`GEMINI.md`](../GEMINI.md)).

## 3. Skills and agent: repeatable procedures

| When | What | File |
|---|---|---|
| After a change | `/sugerir-commit`: reviews **everything** pending, builds a topic → files map and suggests the message. The developer runs it | [`.claude/skills/sugerir-commit/`](../.claude/skills/sugerir-commit/SKILL.md) |
| Starting the environment | `/levantar-proyecto`: diagnoses, starts and confirms with an end-to-end check | [`.claude/skills/levantar-proyecto/`](../.claude/skills/levantar-proyecto/SKILL.md) |
| After changing anything that affects extraction | `/verificar-extraccion`: runs `make check-extraction` (samples × providers against references) and protects Gemini's daily quota | [`.claude/skills/verificar-extraccion/`](../.claude/skills/verificar-extraccion/SKILL.md), [`scripts/check_extraction.py`](../scripts/check_extraction.py) |
| Closing a phase or before a PR to `main` | `revisor-docs` agent (read-only): checks the documentation against the code and against itself | [`.claude/agents/revisor-docs.md`](../.claude/agents/revisor-docs.md) |

Skills also save tokens: one command with compact output replaces dozens of ad-hoc calls returning full JSON.

## 4. Workflow

```text
Agreed phase or task (one at a time, with a report at the end)
  ↓
Branch from develop (never work directly on main/develop)
  ↓
The AI implements + adds tests for the new behavior
  ↓
make verify (same as CI)  →  make check-extraction (if extraction changes)
  ↓
The developer verifies in Postman with real documents (debug_mode saves what each provider received)
  ↓
/sugerir-commit  →  the developer commits  →  PR  →  CI  →  merge
```

Rules that hold the workflow together (all in [`AGENTS.md`](../AGENTS.md)):

- One phase at a time; when done, the AI reports and waits.
- The developer runs installation commands; the AI provides the command.
- Before using an external library or API, the AI checks the official documentation, not its memory (two default AI models were shut down in 2026 without the code noticing: issue 6 in `STATUS.md`).
- Real data only on the developer's machine; tests and samples use fictitious data ([`scripts/generate_samples.py`](../scripts/generate_samples.py)).

## 5. AI mistakes the process caught

The proof that the process works is the mistakes that never reached `main`. Each one changed the process, not just the code:

| AI mistake | How it was caught | What changed in the process |
|---|---|---|
| Reported as fixed an OCR returning 337 characters of noise | The developer asked for quality, not quantity | `make smoke` counts card labels, not characters ([issue 19](./project/STATUS.md)) |
| Changed the local port and domain without checking how they were used | Developer review | Rule in `AGENTS.md`: never change domain or port without asking |
| Commit messages that did not cover every file | Developer review | Mandatory "topic map" step in `/sugerir-commit` |
| Assumed grayscale caused the poor OCR | The developer asked to evaluate it | 7 variants measured: the cause was the card's size on the page ([`PROJECT_PLAN.md` → Image Processing](./project/PROJECT_PLAN.md)) |
| Groq read `05/10/2026` month first when asked for ISO dates | Live check | The AI returns the printed date and the app normalizes it ([`date_normalizer.py`](../app/utils/date_normalizer.py)) |
| `debug_mode` saved nothing for digital PDFs; Gemini never got the document | The developer tested a real CFE bill | Per-request debug independent of OCR; Gemini gets the PDF of the requested pages (issues 21 and 22) |
| A daily-quota 429 was reported as "overloaded" | Developer test | The message says which quota and when it resets (issue 23) |
| A test passed in Docker and failed in CI | The PR's CI run | `make verify` reproduces the CI environment (issue 24) |
| A real INE looked valid when tested, but `validation.valid` was `false`: the OCR read `0` as `O` at CURP position 17, a change the check digit cannot detect, and the CURP vs birth date rule flagged it | Review of that request's debug snapshot | Global `verdict` always visible, and the century resolved from the birth date ([ADR 0001](./decisions/0001-business-validation-rules.md)) |
| The `.env` hook denied `.env*` only where a real `.env` existed (bash expanded the wildcard) | CI on the PR to `main` | `make verify` runs on a clean copy, and the hook tests run in empty and populated folders (issue 26). It also showed that branches need protection: that PR was merged with a red check |

## 6. Limits (to avoid overselling)

- No CD: deployment is not automated.
- There is a single custom agent (`revisor-docs`), used only at defined moments.
- Hooks only protect inside Claude Code; with other tools, the rules depend on the tool.
- `make check-extraction` makes real calls and spends quota: it does not run in CI.
