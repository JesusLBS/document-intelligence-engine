# Status

**Read this first for "what phase are we in and what's next."** Scope and reasoning of each phase live in [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) → Project Roadmap — open it only when you need the *why*.

Last updated: 2026-10-25

## Current phase

**Phase 4 — Business Validation, INE** — `feature/ine-validation` (**in progress**): [ADR 0001](../decisions/0001-business-validation-rules.md) accepted (deterministic rules in the app, AI observations as data, "today" in `Config.TZ`, HTTP 200 with a `validation` block); INE formats stabilized (birth date ISO, expiration `YYYY`, CURP copied as printed + recovery from text); rules engine in `app/rules/` with 8 INE rules. Live check with Groq on `ine_sample.pdf`: 8/8 rules passed on 28 consecutive runs; a bill sent as INE is rejected by `ine.document_detected`. Developer's real INE: `ine.curp_matches_birth_date` failed (OCR read the CURP homoclave `0` as `O`, invisible to the check digit) and it went unnoticed without a global answer → added `data.verdict` and `resolve_curp_century`; re-evaluated locally on that request's snapshot (no new provider call): invalid → valid, 8/8. Pending: the developer's re-check in Postman.

**Next target:** Phase 4 for CSF, then comprobante de domicilio (each one: field formats, then its rules in `registry.py`). With the three done, version 1 is complete.

Done before:
- Alignment before Phase 4: `docs/ai-workflow-and-cleanup` (PR #7) and its CI fix `fix/ci-env-hook-glob` (PR #9, issue 26); `develop` promoted to `main`.
- Phase 2 for the three types: `feature/address-proof-extraction` (PR #6) — comprobante de domicilio via AI, INE and comprobante AI-only, `estado_cuenta` / `licencia_profesional` dropped, Gemini reads the PDF of the requested pages, debug snapshot for any document, quota errors (issues 21–24).
- Code audit fixes (audit of 2026-10-17, list below), each fix with a test that fails on the old code: `fix/api-correctness` (PR #2, issues 1–5), `fix/ai-providers-and-ocr` (PR #3, issues 6–9, 12, 14, 18), `chore/hardening-cleanup` (PR #4, issues 10, 11, 13, 15–17), `fix/ocr-quality-and-regressions` (PR #5, issues 7, 19, 20 + regression check).
- PR #1: single AI context (`AGENTS.md`), docs aligned with the code, status centralized here, protected-branch convention, CI with pytest, Docker-first dev environment (`Makefile` + `scripts/`, healthcheck, `.test` domain checks, `.env` out of the image).

## Phase checklist

Version 1 = Phases 1, 2, 4 and 6 for INE, CSF and comprobante de domicilio. Phases 3 and 5 are possible extensions, not planned work (PROJECT_PLAN.md → Project Roadmap).

| Phase | Status | Notes |
|---|---|---|
| 1 — Core Platform | done | API, PDF diagnosis, Tesseract OCR, factories, standard responses, validation, Docker + nginx |
| 2 — Data Extraction | done | CSF regex; INE and comprobante via AI (Gemini reads the PDF, Groq the text); CURP hints; ID and date normalizers. Real INE, CSF and CFE bill verified by the developer |
| 3 — File Processors | possible extension | Not planned. `app/processors/{image,excel,csv,word}/` are empty extension points |
| 4 — Business Validation | in progress | INE: 8 rules (in review). Next: CSF, then comprobante de domicilio |
| 5 — More AI Providers | possible extension | Gemini and Groq are part of Phase 2; OpenAI, Claude, Azure, AWS not planned |
| 6 — Quality & Observability | in progress | CI on every PR; 228 tests (API, business rules, service, extractors with mocked HTTP, OCR, normalizers, debug store, Claude Code hooks); `make verify` reproduces CI; `make check-extraction` for live checks. Pending: Postman screenshots refresh |

## What works today

| Area | Notes |
|---|---|
| `GET /api/v1/health`, `POST /api/v1/documents/process` | Standard `{ok, status, message, data, meta}` envelope; 404/405 and validation errors keep their status |
| PDF processing (PyMuPDF) | Metadata, page range, multi-signal OCR diagnosis; non-PDF content → 422 |
| OCR (Tesseract) | Requested pages rendered at 400 DPI, cropped to the content area in color (no grayscale), PSM 3 with PSM 11 fallback; CURP / clave de elector look-alike errors corrected by position. Measurement in PROJECT_PLAN.md → Image Processing |
| `from_page` / `to_page` | Respected by everything: text, OCR, rendered pages, the file sent to Gemini and the debug snapshot |
| `debug_mode=true` | Any document, with or without OCR: original file, page images of the range, file and text each extractor received, request summary and result in `storage/debug/{request_id}/` |
| CSF with `extractor=regex` | `CsfExtractor`, unit-tested and covered end-to-end with a generated PDF; real CSF verified by the developer in Postman (2026-10-25) |
| Any type with `extractor=ai` | Gemini (reads the PDF of the requested pages, digital or scanned; default `gemini-3.6-flash`) or Groq (OCR text only; default `openai/gpt-oss-120b`), selectable per request; JSON mode; provider failures → 502/503/504 with a clear message. `ine` and `comprobante_domicilio` default to `ai` |
| INE (scanned) | Gemini 7/7 fields (`gemini-2.5-flash` and `gemini-3.6-flash`; also 7/7, identical on 3 runs, reading the PDF instead of the crop); Groq 6–7/7 (was 0 before the OCR fixes). Developer verified a real INE in Postman with both providers |
| Comprobante de domicilio | Real CFE bill verified by the developer with Groq and Gemini. 16 default fields (holder, itemized address, provider, service type and number, issue date, billed period, due date); dates as ISO. Synthetic samples: digital bill 16/16 and scanned bill 15/16 (no interior number printed) on Groq and Gemini |
| `ine`, `comprobante_domicilio` with `extractor=regex` | 422 — AI-only types (no regex extractor) |
| INE business validation | `verdict` (valid / invalid / incomplete / not_validated) + `validation` block with 8 rules: required fields, `documento_detectado` (hybrid), CURP structure + check digit, clave de elector structure, not expired (Mexico's date), CURP vs birth date, clave vs CURP (date and sex), name initials (warning). `null` with custom `fields` |
| `make check-extraction` | Live extraction vs `samples/expected` (Groq by default, Gemini on request). Today: both comprobante samples 15/15, INE 6/6 (dates and `documento_detectado` added), on Groq |
| AI guardrails | Claude Code hooks deny commits and any access to `.env*` (29 hook tests); `revisor-docs` agent for phase closes / PRs to `main` |

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
| 6 | Default `GEMINI_MODEL=gemini-2.0-flash` was shut down on 2026-06-01 ([deprecations](https://ai.google.dev/gemini-api/docs/deprecations)); default `GROQ_MODEL=llama-3.3-70b-versatile` was shut down on 2026-08-16 ([deprecations](https://console.groq.com/docs/deprecations)); `thinkingBudget` is legacy on Gemini 3 | fixed — `fix/ai-providers-and-ocr` |
| 7 | Tesseract default `--psm 3` returned 0 chars on a photographed ID card; regex and Groq silently got empty text | fixed — PSM fallback in `fix/ai-providers-and-ocr`, completed by issue 19 |

### Robustness and security

| # | Issue | Status |
|---|---|---|
| 8 | AI provider failures (non-200, blocked response → `KeyError`, empty API key still sent) end as a generic 500 instead of a clear 502/503 | fixed — `fix/ai-providers-and-ocr` |
| 9 | nginx default `proxy_read_timeout` is 60 s; OCR at 300 DPI + up to 60 s of Gemini can exceed it (504) | fixed — `fix/ai-providers-and-ocr` |
| 10 | `MAX_CONTENT_LENGTH` not set: Flask reads the whole upload before the size check | fixed — `chore/hardening-cleanup` |
| 11 | `index.py` hardcoded `debug=True` (ignored `APP_DEBUG`) and enabled the interactive Werkzeug debugger (in practice never rendered, since the global handler answers every error as JSON) | fixed — `chore/hardening-cleanup` |
| 12 | Personal data in logs: failed AI parse logs 200 chars of the AI response (names, CURP); CURP initials logged | fixed — `fix/ai-providers-and-ocr` |
| 13 | `meta.request_id` differs from the internal/log request id; `ResponseHelper` reads `APP_ENV` with a default different from `Config` | fixed — `chore/hardening-cleanup` |
| 14 | AI JSON parsing uses `.strip("```json")` (strips characters, not a prefix); both APIs offer native JSON mode | fixed — `fix/ai-providers-and-ocr` |

### Cleanup and design

| # | Issue | Status |
|---|---|---|
| 15 | `DocumentService` branches on `isinstance(extractor, AiExtractor)` (extract signatures differ), contradicting the DIP described in PROJECT_PLAN.md | fixed — `chore/hardening-cleanup` |
| 16 | Dead code: `ExtractorNotFoundException`, unused `language` field, unused `matches` in `CsfExtractor`, empty `processors/interfaces/`, duplicated `load_dotenv` | fixed — `chore/hardening-cleanup` |
| 17 | `debug_mode` wipes other requests' debug folders; `storage/logs/app.log` grows without rotation | fixed — `chore/hardening-cleanup` |
| 18 | `make smoke` only checks `ok:true`, so it passed while OCR returned 0 chars (issue 7) | fixed — `fix/ai-providers-and-ocr` |
| 19 | After the PSM fallback the OCR text was still noise (337 chars, 17 words, no card labels): full grayscale page where the card is small; `make smoke` measured length, not quality | fixed — `fix/ocr-quality-and-regressions` (crop to content in color, 400 DPI, ID normalizer, smoke checks card labels) |
| 20 | Docs said to run `make restart` after editing `.env`; it does not reload `env_file` (verified: old key and model kept), `make up` does | fixed — `fix/ocr-quality-and-regressions` |
| 21 | `debug_mode=true` saved nothing for digital PDFs: debug images were written inside the OCR step, which does not run when the PDF has embedded text (found by the developer with a real CFE bill) | fixed — `feature/address-proof-extraction` (`DebugStore`, per request, independent of OCR) |
| 22 | Gemini only got a page image when OCR ran: a digital PDF reached it as embedded text only (`with_images=False`), out of order on a real CFE bill, and it returned 1 field while Groq did better | fixed — `feature/address-proof-extraction` (Gemini gets the PDF of the requested pages, inline base64) |
| 23 | A Gemini 429 "quota exceeded" (free tier: 20 requests per day per model on `gemini-3.6-flash`) was reported as "temporarily unavailable, try again later", and the log cut the error before the quota name | fixed — `feature/address-proof-extraction` (message says which quota and when it resets; Groq's Retry-After is read too) |
| 24 | CI failed on the PR: the new debug-snapshot test rendered pages with pdf2image, which needs poppler; the container has it, the CI runner does not, and `make verify` ran inside the container, so it passed locally | fixed — `feature/address-proof-extraction` (test stubs the renderer; `make verify` hides poppler/tesseract from PATH like CI) |
| 25 | `make verify` (issue 24 fix) trimmed PATH to Python's bin: it hid poppler/tesseract as intended but also bash/grep/sed, which the CI runner has, so the new hook tests failed only locally | fixed — `docs/ai-workflow-and-cleanup` (failing stubs for poppler/tesseract placed first on PATH instead) |
| 26 | CI red after `docs/ai-workflow-and-cleanup`: `block-env-access.sh` looped over unquoted values, so bash expanded `.env*` as a filename glob. It was denied only where a real `.env` existed (the developer's clone, where `make verify` ran) and allowed in CI. The PR was merged anyway (no branch protection) | fixed — `fix/ci-env-hook-glob` (`set -f` in the hook; tests run the hook in empty and populated folders; `make verify` now runs on a clean copy of the files git would commit, like the CI checkout) |

### Regression check against the pre-session code (2026-10-25)

Same sample (`samples/pdf/ine_sample.pdf`) and request, original code (commit `8b6e98e`) vs current code:

| Strategy | Original | Current |
|---|---|---|
| `extractor=ai`, Gemini (`gemini-2.5-flash`) | 7/7 fields | 7/7 fields — no regression |
| `extractor=ai`, Groq (`openai/gpt-oss-120b`) | 0 fields (OCR returned nothing; Groq was never called) | 6/7 fields, 6 matching Gemini |
| `extractor=regex` | 0 fields (no INE regex extractor) | 0 fields (same) |

Groq on embedded text (generated CSF with fictitious data): RFC and CURP exact, `padron_status` and name filled.

### Live verification of `feature/address-proof-extraction` (2026-10-25)

Through nginx, synthetic samples from `scripts/generate_samples.py`:

| Sample | Groq (`openai/gpt-oss-120b`) | Gemini (`gemini-3.6-flash`) |
|---|---|---|
| `comprobante_luz_sample.pdf` (digital, embedded text) | 16/16, ~1.5 s | 16/16, ~1.9 s |
| `comprobante_internet_scan_sample.pdf` (image only → OCR) | 15/16 ×3 runs, ~2.1 s | 15/16, ~3.2 s |

- First run asked for ISO dates: Groq returned `05/10/2026` as `2026-05-10` (month first). Fixed by asking for dates as printed and converting in the app; after that, all dates correct on every run.
- Regressions: INE Gemini 7/7, Groq 6/7 (same as before); CSF regex RFC/CURP/`padron_status` exact; `make smoke` OK (7/10 card labels; it now sends `document_type=csf` + regex, since INE rejects regex).
- After issues 21–22, on a 2-page PDF (page 1 digital bill, page 2 scanned bill) with `debug_mode=true`: range 1-1 → page 1 data on Groq and Gemini (16/16), range 2-2 → page 2 data (15/16); `sent_to_ai.pdf` had 1 page; debug folders complete for digital and scanned pages; Gemini log `with_document=True document_mime_type=application/pdf`. INE on Gemini reading the PDF: 7/7, identical on 3 runs; Groq 7/7 with a one-letter OCR difference in the surnames (initials match the CURP on both).

### Live verification of `fix/ai-providers-and-ocr` (2026-10-25)

- OCR on `samples/pdf/ine_sample.pdf`: 0 → 337 chars (PSM 11 fallback); `make smoke` now fails if OCR returns < 50 chars.
- Gemini: `gemini-2.0-flash` → 404 "no longer available"; `gemini-2.5-flash` + `thinkingLevel` → 400 (hence the gemini-2.x guard); the new payload (`responseMimeType` + `thinkingLevel: low`) → 200 on `gemini-3.6-flash` and `gemini-3.5-flash-lite`; full multimodal extraction → 7/7 fields on `gemini-2.5-flash`.
- Full multimodal extraction on Gemini 3: verified on 2026-10-25 with `gemini-3.6-flash` (INE 7/7, scanned comprobante; model confirmed in the request logs). One INE call got a 503 "high demand" first and succeeded on retry.
- Groq: verified live after the key rotation (see regression check above).

## Open, non-blocking follow-ups

- Retry with backoff on provider 503 (Gemini 3 models were saturated during testing) — today the client gets a clear 503 and must retry. Not for 429 daily quota: retrying cannot help there.
- INE reference for `make check-extraction`: add the surnames from Gemini (`--provider gemini --print-reference`) when its quota allows (Groq differs by one OCR letter). Also run the INE validation once on Gemini.
- Groq on the INE sample: about 1 run in 30 still returned a CURP different from the reference (seen once in `make check-extraction`, not reproduced in 28 later runs); a wrong CURP shows up in `validation` (check digit / birth date rules).
- Phase 4 note: real CFE bills print no issue date (`fecha_emision` comes back null), so the document-age rule must fall back to `periodo_fin` (or the due date); the cut-off date ("corte a partir de") is not extracted yet.
- Postman screenshots: none for the comprobante; the INE one predates the PDF input to Gemini (developer's own action).
- Gemini free tier: 20 requests per day per model (enforcement is approximate: a 429 said ~8.9 h and a call passed 83 s later). Enabling billing on the Google AI project (developer's decision) removes it; until then, live tests should prefer Groq.

- Enable branch protection on `main` and `develop` in GitHub, requiring the `Tests / pytest` check (manual, developer's own action; requires a public repo or a paid plan for private repos). Without it, the PR of issue 26 could be merged with a red check.
- Lint/format (ruff) — deferred to avoid a large unrelated diff.
- The Docker image runs Flask's development server (`python index.py`, debug on). Fine for local use; a production-like setup would need a WSGI server (e.g. gunicorn) and debug off.
- `samples/pdf/ine_sample.pdf` is a public internet example of an INE; consider replacing it with a fully synthetic sample for the portfolio.
- Second check of the comprobante with a public sample bill downloaded from the internet (developer), after the real-bill check.

## How to keep this file honest

Update this file every time a phase starts or finishes, a bug is fixed or found, or the next target changes. This is the **only** place current status is asserted: `README.md`, `docs/README.en.md` and `PROJECT_PLAN.md` link here instead of restating it.
