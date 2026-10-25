# Status

**Read this first for "what phase are we in and what's next."** Scope and reasoning of each phase live in [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) → Project Roadmap — open it only when you need the *why*.

Last updated: 2026-10-17

## Current phase

Code audit fixes (audit of 2026-10-17, list below), in three branches off `develop`, each fix with a test that fails on the old code:

1. `fix/api-correctness` — **in progress**: issues 1–5.
2. `fix/ai-providers-and-ocr` — next: issues 6–9, 12, 14, 18.
3. `chore/hardening-cleanup` — after: issues 10, 11, 13, 15–17.

Done before (merged in PR #1): single AI context (`AGENTS.md`), docs aligned with the code, status centralized here, protected-branch convention, CI with pytest, Docker-first dev environment (`Makefile` + `scripts/`, healthcheck, `.test` domain checks, `.env` out of the image).

**Next target after the audit:** Phase 4 — Business Validation, on top of the test suite built during the fixes.

## Phase checklist

| Phase | Status | Notes |
|---|---|---|
| 1 — Core Platform | done | API, PDF diagnosis, Tesseract OCR, factories, standard responses, validation, Docker + nginx |
| 2 — Data Extraction | partial | Done: CSF regex, AI extraction (Gemini multimodal, Groq text-only), CURP hints. Missing: regex extractors for INE/comprobante/etc., default fields for `estado_cuenta` and `licencia_profesional` |
| 3 — File Processors | not started | `app/processors/{image,excel,csv,word}/` are empty scaffolds |
| 4 — Business Validation | not started | Defined in PROJECT_PLAN.md only |
| 5 — AI Providers | partial | Gemini and Groq done; OpenAI, Claude, Azure, AWS not started |
| 6 — Quality & Observability | in progress | CI active on PRs (`.github/workflows/tests.yml`). Tests: CSF extractor, PdfProcessor, DocumentService uploads, API errors/validation/pipeline (30 tests) |

## What works today

| Area | Notes |
|---|---|
| `GET /api/v1/health`, `POST /api/v1/documents/process` | Standard `{ok, status, message, data, meta}` envelope; 404/405 and validation errors keep their status |
| PDF processing (PyMuPDF) | Metadata, page range, multi-signal OCR diagnosis; non-PDF content → 422 |
| OCR (Tesseract) | Grayscale preprocessing only (OpenCV pipeline was removed, see PROJECT_PLAN.md → Image Processing). **Returns no text on photographed ID cards — issue 7** |
| CSF with `extractor=regex` | `CsfExtractor`, unit-tested and covered end-to-end with a generated PDF |
| Any type with `extractor=ai` | Gemini (text + page images) or Groq (text only), selectable per request. **Default Gemini model is shut down — issue 6** |
| `ine`, `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` with `extractor=regex` | Return empty `extractedFields` (PassthroughExtractor) |

## Code audit (2026-10-17)

Each item was verified against the running API, a measurement or official docs. Mark it fixed here (with the branch) when it merges.

### Bugs

| # | Issue | Status |
|---|---|---|
| 1 | Unknown route / wrong method returned 500 (the `Exception` handler swallowed Werkzeug `HTTPException`) | fixed — `fix/api-correctness` |
| 2 | Unknown `provider` → 500 `ValueError`; unknown `extractor` silently ran regex (not validated by the schema) | fixed — `fix/api-correctness` |
| 3 | Controller re-parsed the form and ignored `schema.load()`: `include_raw_text=1` / `force_ocr=1` read as false, `fields[]` validated but dropped | fixed — `fix/api-correctness` |
| 4 | `.pdf` file with non-PDF content → 500; document left open if page-range validation raised | fixed — `fix/api-correctness` |
| 5 | Upload saved as `temp_{pid}`: concurrent requests (threaded dev server) could overwrite each other's file | fixed — `fix/api-correctness` |
| 6 | Default `GEMINI_MODEL=gemini-2.0-flash` was shut down on 2026-06-01 ([deprecations](https://ai.google.dev/gemini-api/docs/deprecations)); `thinkingConfig` and the Groq model also need checking against current docs | open |
| 7 | Tesseract default `--psm 3` returns 0 chars on a photographed ID card (`--psm 11`: 337 chars); regex and Groq silently get empty text | open |

### Robustness and security

| # | Issue | Status |
|---|---|---|
| 8 | AI provider failures (non-200, blocked response → `KeyError`, empty API key still sent) end as a generic 500 instead of a clear 502/503 | open |
| 9 | nginx default `proxy_read_timeout` is 60 s; OCR at 300 DPI + up to 60 s of Gemini can exceed it (504) | open |
| 10 | `MAX_CONTENT_LENGTH` not set: Flask reads the whole upload before the size check | open |
| 11 | `index.py` hardcodes `debug=True` (ignores `APP_DEBUG`); Werkzeug debugger reachable on port 80 from the LAN | open |
| 12 | Personal data in logs: failed AI parse logs 200 chars of the AI response (names, CURP); CURP initials logged | open |
| 13 | `meta.request_id` differs from the internal/log request id; `ResponseHelper` reads `APP_ENV` with a default different from `Config` | open |
| 14 | AI JSON parsing uses `.strip("```json")` (strips characters, not a prefix); both APIs offer native JSON mode | open |

### Cleanup and design

| # | Issue | Status |
|---|---|---|
| 15 | `DocumentService` branches on `isinstance(extractor, AiExtractor)` (extract signatures differ), contradicting the DIP described in PROJECT_PLAN.md | open |
| 16 | Dead code: `ExtractorNotFoundException`, unused `language` field, unused `matches` in `CsfExtractor`, empty `processors/interfaces/`, duplicated `load_dotenv` | open |
| 17 | `debug_mode` wipes other requests' debug folders; `storage/logs/app.log` grows without rotation | open |
| 18 | `make smoke` only checks `ok:true`, so it passed while OCR returned 0 chars (issue 7) | open |

## Open, non-blocking follow-ups

- Enable branch protection on `main` and `develop` in GitHub (manual, developer's own action; requires a public repo or a paid plan for private repos).
- Lint/format (ruff) — deferred to avoid a large unrelated diff.
- The Docker image runs Flask's development server (`python index.py`, debug on). Fine for local use; a production-like setup would need a WSGI server (e.g. gunicorn) and debug off.
- `samples/pdf/ine_sample.pdf` is a public internet example of an INE; consider replacing it with a fully synthetic sample for the portfolio.

## How to keep this file honest

Update this file every time a phase starts or finishes, a bug is fixed or found, or the next target changes. This is the **only** place current status is asserted: `README.md`, `docs/README.en.md` and `PROJECT_PLAN.md` link here instead of restating it.
