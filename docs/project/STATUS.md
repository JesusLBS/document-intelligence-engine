# Status

**Read this first for "what phase are we in and what's next."** Scope and reasoning of each phase live in [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) → Project Roadmap — open it only when you need the *why*.

Last updated: 2026-10-17

## Current phase

Repo housekeeping (branch `chore/ai-context-and-ci`): single AI context (`AGENTS.md`), docs aligned with the code, status centralized here, protected-branch convention and CI with pytest.

**Next target:** decide between (a) raising test coverage (services, factories, API with mocked OCR/AI) while fixing the open bugs below, or (b) starting Phase 4 — Business Validation. Recommendation: (a) first, so Phase 4 is built on top of a test safety net.

## Phase checklist

| Phase | Status | Notes |
|---|---|---|
| 1 — Core Platform | done | API, PDF diagnosis, Tesseract OCR, factories, standard responses, validation, Docker + nginx |
| 2 — Data Extraction | partial | Done: CSF regex, AI extraction (Gemini multimodal, Groq text-only), CURP hints. Missing: regex extractors for INE/comprobante/etc., default fields for `estado_cuenta` and `licencia_profesional` |
| 3 — File Processors | not started | `app/processors/{image,excel,csv,word}/` are empty scaffolds |
| 4 — Business Validation | not started | Defined in PROJECT_PLAN.md only |
| 5 — AI Providers | partial | Gemini and Groq done; OpenAI, Claude, Azure, AWS not started |
| 6 — Quality & Observability | in progress | CI added (`.github/workflows/tests.yml`, pytest on PR/push to `main`/`develop`; first run pending on this branch's PR). Tests: only `tests/extractors/test_csf_extractor.py` |

## What works today

| Area | Notes |
|---|---|
| `GET /api/v1/health`, `POST /api/v1/documents/process` | Standard `{ok, status, message, data, meta}` envelope |
| PDF processing (PyMuPDF) | Metadata, page range, multi-signal OCR diagnosis |
| OCR (Tesseract) | Grayscale preprocessing only (OpenCV pipeline was removed, see PROJECT_PLAN.md → Image Processing) |
| CSF with `extractor=regex` | `CsfExtractor`, unit-tested |
| Any type with `extractor=ai` | Gemini (text + page images) or Groq (text only), selectable per request |
| `ine`, `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` with `extractor=regex` | Return empty `extractedFields` (PassthroughExtractor) |

## Open bugs (found 2026-10-17, not fixed yet)

1. `DocumentService._save` names the upload `temp_{pid}`: concurrent requests in the same process overwrite each other's file.
2. `extractor` and `provider` are not validated by the schema: unknown `provider` → `ValueError` → 500 instead of 422; unknown `extractor` silently runs regex.
3. `DocumentController.process` re-parses the form by hand and ignores `schema.load()` output, so booleans can disagree with what validation accepted (e.g. `include_raw_text=1`).
4. `ResponseHelper` reads `APP_ENV` from `os.environ` with default `production` (Config defaults to `local`); `meta.request_id` is not the request id used internally/in logs.
5. To verify: default `GEMINI_MODEL=gemini-2.0-flash` combined with `thinkingConfig` in `GeminiExtractor` — check against current Gemini API docs.

## Open, non-blocking follow-ups

- Enable branch protection on `main` and `develop` in GitHub (manual, developer's own action; requires a public repo or a paid plan for private repos).
- Lint/format (ruff) — deferred to avoid a large unrelated diff.
- `language` request field is accepted but unused (Tesseract language is hardcoded to `spa`).

## How to keep this file honest

Update this file every time a phase starts or finishes, a bug is fixed or found, or the next target changes. This is the **only** place current status is asserted: `README.md`, `docs/README.en.md` and `PROJECT_PLAN.md` link here instead of restating it.
