# Document Intelligence Engine

> Spanish version: [README.md](../README.md)

## Developed by: Jesus Chicho Hernández

Python/Flask API for document processing with AI, design patterns, and clean architecture. Portfolio project demonstrating how to transform unstructured documents (PDF) into structured data through an extensible pipeline: OCR diagnosis, regex or AI extraction, and standardized JSON responses.

This is not a standalone OCR script: it is a document intelligence platform where OCR, extractors, and AI providers are interchangeable layers.

---

## What does this project solve?

It receives PDF documents (native or scanned), analyzes their content, decides whether OCR is required, extracts relevant fields based on document type, and returns a structured response ready for validation or automation workflows.

Current use cases:

- **CSF** (Mexican tax status certificate): regex extraction of RFC, CURP, name, tax regime, etc.
- **INE** (Mexican voter ID): AI extraction with CURP hints and multimodal support (Gemini).
- **Comprobante de domicilio** (proof of address: electricity, water, gas, phone, internet bills): AI extraction of holder, itemized address, provider, service number and dates normalized to ISO.

---

## Technical highlights

- **Clean architecture**: Controller → Service → Factory → Processor/Extractor, with contracts and dependency inversion.
- **Design patterns**: Strategy (processors, extractors, OCR) and Factory (dynamic selection by file and document type).
- **Smart PDF pipeline**: PyMuPDF diagnoses text density and chooses between embedded extraction or OCR.
- **OCR**: pages rasterized at 400 DPI and cropped to their content area (color, no grayscale), Tesseract with sparse-text fallback, and positional correction of typical OCR errors in CURP and clave de elector.
- **Interchangeable AI**: `AiExtractor` with Gemini (PDF of the requested pages + text) and Groq (text-only) providers.
- **Input validation**: Marshmallow schemas, centralized exceptions, structured logging.
- **Containerization and CI**: Docker + nginx as reverse proxy; GitHub Actions runs pytest on every PR.

---

## Built with AI, under verifiable rules

This project is built with **Claude Code as the coding agent**: the AI implements, and the developer defines architecture and scope, reviews, verifies with real documents and makes the commits. What matters is enforced by code, not by trusting the model:

- **A single context source** for any AI ([`AGENTS.md`](../AGENTS.md)), with status and plan kept apart.
- **Technical guardrails with tests:** hooks that stop the AI from committing or reading `.env`, a `pre-push` hook protecting `main`/`develop`, CI on every PR and `make verify` reproducing CI.
- **Skills and an agent** for repeatable work: suggesting commits, starting the environment, checking extraction against references (`make check-extraction`) and auditing the documentation.
- **AI mistakes caught by the process**, documented with the change each one left behind.

Details, files and real cases: **[docs/AI_WORKFLOW.en.md](./AI_WORKFLOW.en.md)**

---

## Project status

Current phase, what works today, known bugs and next step: **[docs/project/STATUS.md](./project/STATUS.md)** (single source of status).

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Framework | Flask 3 |
| PDF | PyMuPDF, pdf2image |
| OCR | Tesseract, pytesseract |
| Image | Pillow |
| Validation | Marshmallow |
| AI | Google Gemini, Groq (HTTP via `requests`) |
| Tests | pytest |
| Infra | Docker, nginx, GitHub Actions |

---

## Architecture

```text
Client
  ↓
POST /api/v1/documents/process
  ↓
Controller → DocumentService
  ↓
DocumentProcessorFactory → PdfProcessor
  ↓
Diagnosis (OCR required?)
  ├── NO  → Embedded text extraction
  └── YES → TesseractOcr (requested pages cropped to content → text)
  ↓
ExtractorFactory
  ├── CsfExtractor (regex)
  ├── AiExtractor → Gemini (PDF of the requested pages + text) / Groq (text only)
  └── PassthroughExtractor (regex fallback)
  ↓
JSON Response (camelCase fields)
```

Design, patterns and architecture decisions: [docs/project/PROJECT_PLAN.md](./project/PROJECT_PLAN.md)

---

## Repo structure

```text
document-intelligence-engine/
├── app/
│   ├── config/              # Config (single source of env settings) + logging
│   ├── contracts/           # DocumentProcessorInterface
│   ├── controllers/         # DocumentController (no business logic)
│   ├── exceptions/          # AppException + global handler
│   ├── extractors/          # BaseExtractor, CsfExtractor, AiExtractor, PassthroughExtractor (fallback), ExtractionContext
│   │   └── ai/              # BaseAiExtractor, GeminiExtractor, GroqExtractor
│   ├── factories/           # DocumentProcessorFactory, ExtractorFactory
│   ├── helpers/             # ResponseHelper, Logger, request_context (request id), DebugStore (debug_mode)
│   ├── ocr/                 # BaseOcr, TesseractOcr
│   ├── processors/
│   │   ├── base/
│   │   ├── pdf/             # PdfProcessor (diagnosis, requested pages), page_renderer (render + crop)
│   │   └── image/ excel/ csv/ word/   # empty extension points (possible extensions, see PROJECT_PLAN)
│   ├── routes/              # /api/v1 blueprint
│   ├── schemas/             # Marshmallow schemas
│   ├── services/            # DocumentService (orchestrator)
│   ├── utils/               # curp_decoder, case_converter, id_normalizer (CURP/clave), date_normalizer (ISO)
│   └── validators/          # Request validation (decorator)
├── tests/                   # pytest (includes the Claude Code hooks)
├── docs/
│   ├── project/             # PROJECT_PLAN.md (design and roadmap), STATUS.md (status)
│   ├── screenshots/         # Postman screenshots used in the README
│   ├── AI_WORKFLOW.md       # How it is developed with AI (and AI_WORKFLOW.en.md)
│   └── README.en.md         # This file
├── docker/                  # Dockerfile (Python 3.12 + Tesseract + poppler)
├── nginx/                   # Reverse proxy
├── scripts/                 # up, verify, smoke, doctor, check_extraction (called by the Makefile) and generate_samples.py
├── samples/                 # pdf/: public INE and fictitious address proofs · expected/: make check-extraction references
├── storage/                 # debug/, logs/ (runtime, git-ignored)
├── uploads/                 # Temporary uploads (git-ignored)
├── .github/workflows/       # CI (pytest)
├── .githooks/               # pre-push hook blocking direct pushes to main/develop
├── .claude/                 # Claude Code: hooks (commits, .env), skills and revisor-docs agent
├── AGENTS.md                # Context and rules for any AI assistant
├── CLAUDE.md, GEMINI.md     # Only import AGENTS.md
├── docker-compose.yml
├── Makefile                 # Shortcuts: make up, make test, make verify…
├── index.py                 # Flask entry point
├── requirements.txt
├── NOTICE.txt
└── .env.example
```

---

## Local development

**Docker is the main development environment**: it ships Python 3.12, Tesseract with Spanish and poppler, and it is what the examples in this README use. Running on a local Python is **optional** (see the end of this section).

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- `make` (bundled with macOS/Linux)
- `/etc/hosts` entry: `127.0.0.1 document-intelligence.test` (local domain served by nginx)
- AI keys only if you use `extractor=ai`: `GEMINI_API_KEY` and/or `GROQ_API_KEY`

> **Free AI accounts.** Both keys can be on the free tier, which limits requests (Gemini, October 2026: **20 requests per day per model** on `gemini-3.6-flash`). Past it, the API answers 503 with `exceeded its quota (<quota>, limit N); retry in …`. The wait is the provider's estimate and is not exact (Google said ~9 h and accepted a request 83 s later). Meanwhile, use the other provider (`provider=groq` / `provider=gemini`) or move the account to a paid plan. Current limits: [Gemini](https://ai.google.dev/gemini-api/docs/rate-limits) · [Groq](https://console.groq.com/docs/rate-limits).

`make doctor` checks all of this (read-only, installs nothing).

### First run

```bash
git clone <repo-url>
cd document-intelligence-engine
cp .env.example .env                    # add AI keys if you will use them
echo "127.0.0.1 document-intelligence.test" | sudo tee -a /etc/hosts   # local domain (once per machine)
git config core.hooksPath .githooks     # enable the pre-push hook protecting main/develop
make doctor                             # check prerequisites
make build                              # build the image and start in the background
make smoke                              # health + real OCR on samples/pdf/ine_sample.pdf
```

API at **http://document-intelligence.test** (nginx on port 80 → Flask on app:5000).

### Everyday commands

| Command | What it does |
|---|---|
| `make up` | Start in the background and wait until the API answers (healthcheck). Frees the terminal |
| `make build` | Same, but rebuilds the image. Only needed when `requirements.txt` or the `Dockerfile` change |
| `make down` | Stop and remove the containers |
| `make restart` | Restart only the API process. Does **not** reload `.env`: use `make up` |
| `make logs` | Follow Flask logs. Ctrl+C leaves the logs, **stops nothing** |
| `make ps` | Container status |
| `make shell` | Shell inside the API container |
| `make test` | pytest inside the container (`make test ARGS="-k csf"` to filter) |
| `make verify` | Same checks CI runs; use it before pushing |
| `make smoke` | End-to-end check through nginx (no API keys) |
| `make check-extraction` | Real AI extraction against the `samples/expected` references (Groq by default; `ARGS="--provider all"` adds Gemini, which counts against its daily quota) |
| `make doctor` | Machine prerequisites, `.env`, `/etc/hosts`, port 80 and hooks |

`make` with no arguments lists the commands. Logic lives in `scripts/`; the `Makefile` only provides shortcuts.

- Code is mounted as a volume and Flask runs in debug mode: changes in `app/` reload automatically, no rebuild needed.
- With `restart: unless-stopped`, containers come back when Docker Desktop restarts, unless you stopped them with `make down`.

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The terminal stays streaming logs | `docker compose up` was run without `-d`. Use `make up`. In the foreground, Ctrl+C stops the containers and Ctrl+Z only suspends the terminal job (closing it stops them) |
| `port is already allocated` | Another project was left running on port 80. Stop it (`make down` in that project). `make doctor` shows who holds it |
| `document-intelligence.test` does not respond | Missing `/etc/hosts` entry (`make doctor` checks it) or containers are down (`make ps`) |
| Every request takes ~5 s | `/etc/resolver/test` sends `.test` lookups to Laravel Herd's DNS and Herd is stopped: macOS waits 5 s before using `/etc/hosts`. Start Herd or review that file. `make doctor` detects it (`dns` line) |
| `env file .env not found` | Run `cp .env.example .env` |
| Changed `requirements.txt` and nothing changed | `make build` |
| `extractor=ai` returns 503 | Read the message: **"is not configured"** → the key (`GEMINI_API_KEY` / `GROQ_API_KEY`) is missing in `.env`; add it and `make up` (`make restart` does not reload `.env`). **"exceeded its quota (…)"** → the provider quota is used up: it says which one and when it resets (Gemini's free tier allows 20 requests per day per model); wait or use the other provider. **"temporarily unavailable"** → the provider is overloaded; retry in a few seconds |
| `extractor=ai` returns 502 or 504 | The provider failed: the message says why (HTTP, blocked or truncated answer, timeout). `HTTP 404` usually means a shut-down model: check `GEMINI_MODEL` / `GROQ_MODEL` against the deprecation pages |

### Optional: local Python (no Docker)

Only if you want to run the API or tests outside Docker. Requires Python 3.12 (macOS ships 3.9, which won't work), Tesseract with Spanish and poppler:

```bash
brew install python@3.12 tesseract tesseract-lang poppler
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python index.py      # http://localhost:5000 (no nginx)
pytest tests/ -v
```

---

## Environment variables

See [.env.example](../.env.example). Key variables:

| Variable | Description |
|----------|-------------|
| `APP_ENV` | Environment (`local`, `production`) |
| `APP_DEBUG` | Flask debug mode |
| `MAX_FILE_SIZE_MB` | Max file size (default: 10) |
| `DEFAULT_EXTRACTOR` | Default extractor for `csf` (`regex` or `ai`); `ine` and `comprobante_domicilio` always use `ai` |
| `AI_PROVIDER` | Default AI provider (`gemini` or `groq`) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `GEMINI_MODEL` / `GROQ_MODEL` | Models (default `gemini-3.6-flash` / `openai/gpt-oss-120b`) |
| `GEMINI_THINKING_LEVEL` / `GROQ_REASONING_EFFORT` | Reasoning level (`low`); empty for models that don't support it |

---

## API Endpoints

Base URL: `/api/v1`

Every response carries a `meta.request_id` and the same value in the `X-Request-ID` header; it also appears on every log line (`make logs`), so it traces one specific request. Uploads over the limit (`MAX_FILE_SIZE_MB`) get a 413 or 422.

### GET /health

Checks that the service is running.

**Response:**

```json
{
  "ok": true,
  "status": 200,
  "message": "Success request",
  "data": {
    "message": "Document Intelligence Engine is running"
  },
  "meta": {
    "request_id": "uuid",
    "env": "local",
    "timestamp": "2026-07-11T07:00:00+00:00"
  }
}
```

### POST /documents/process

Processes a PDF document and extracts fields based on type and strategy.

**Content-Type:** `multipart/form-data`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | PDF (max 10 MB) |
| `document_type` | string | Yes | `ine`, `csf`, `comprobante_domicilio` |
| `fields` | list | No | Fields to extract (uses defaults per type if omitted) |
| `extractor` | string | No | `regex` or `ai`. Default: `ai` for `ine` and `comprobante_domicilio` (AI only: `regex` returns 422); `DEFAULT_EXTRACTOR` (`regex`) for `csf` |
| `provider` | string | No | `gemini` or `groq` (only with `extractor=ai`) |
| `force_ocr` | bool | No | Force OCR even when PDF has embedded text |
| `from_page` / `to_page` | int | No | Page range (1-indexed) |
| `all_fields` | bool | No | Extract all detectable fields (AI) |
| `include_raw_text` | bool | No | Include raw text in response (default: `true`) |
| `debug_mode` | bool | No | Save to `storage/debug/{request_id}/` the original file, the requested pages as images, what the extractor received (text and, for Gemini, the PDF of the range) and the result. Works for any document, with or without OCR |

#### CSF example (regex)

```bash
curl -X POST http://document-intelligence.test/api/v1/documents/process \
  -F "file=@csf.pdf" \
  -F "document_type=csf" \
  -F "extractor=regex" \
  -F "fields=rfc" \
  -F "fields=curp" \
  -F "fields=full_name"
```

**Response (partial):**

```json
{
  "ok": true,
  "status": 200,
  "message": "Success request",
  "data": {
    "fileType": "pdf",
    "pages": 2,
    "processedPages": { "from": 1, "to": 2 },
    "hasText": true,
    "isScanned": false,
    "processingMethod": "text_extraction",
    "ocrRequired": false,
    "extractedFields": {
      "rfc": "XAXX010101AAA",
      "curp": "XAXX010101HDFAAA09",
      "fullName": "JUAN PEREZ LOPEZ"
    },
    "diagnosis": {
      "reason": "embedded_text_found",
      "confidence": "high"
    }
  }
}
```

#### INE example (ai + gemini)

```bash
curl -X POST http://document-intelligence.test/api/v1/documents/process \
  -F "file=@ine.pdf" \
  -F "document_type=ine" \
  -F "extractor=ai" \
  -F "provider=gemini" \
  -F "include_raw_text=false"
```

**Response (partial):**

```json
{
  "ok": true,
  "status": 200,
  "message": "Success request",
  "data": {
    "fileType": "pdf",
    "processingMethod": "ocr",
    "ocrRequired": true,
    "extractedFields": {
      "nombre": "JUAN",
      "apellidoPaterno": "PEREZ",
      "apellidoMaterno": "LOPEZ",
      "curp": "XAXX010101HDFAAA09",
      "claveElector": "PRPLJN01010109H000"
    },
    "text": null
  }
}
```

#### Address proof example (ai)

AI only (`extractor` omitted: it is the default for `ine` and `comprobante_domicilio`). Works for electricity, water, gas, phone or internet bills, digital or scanned. Dates come back as ISO (`YYYY-MM-DD`); the app converts them from the printed format (`14 OCT 26`, `05/10/2026`, always day first).

```bash
curl -X POST http://document-intelligence.test/api/v1/documents/process \
  -F "file=@samples/pdf/comprobante_luz_sample.pdf" \
  -F "document_type=comprobante_domicilio" \
  -F "provider=groq" \
  -F "include_raw_text=false"
```

**Response (partial, fictitious sample):**

```json
"extractedFields": {
  "nombreTitular": "XAVIER EJEMPLO PRUEBA",
  "domicilioCompleto": "AV DE LOS EJEMPLOS 123 INT 4, COL. CENTRO, CUAUHTEMOC, CIUDAD DE MEXICO, C.P. 06000",
  "calle": "AV DE LOS EJEMPLOS",
  "numeroExterior": "123",
  "numeroInterior": "4",
  "colonia": "CENTRO",
  "municipio": "CUAUHTEMOC",
  "estado": "CIUDAD DE MEXICO",
  "codigoPostal": "06000",
  "proveedor": "ENERGIA DEL VALLE S.A. DE C.V.",
  "tipoServicio": "luz",
  "numeroServicio": "000123456789",
  "fechaEmision": "2026-10-14",
  "periodoInicio": "2026-08-12",
  "periodoFin": "2026-10-13",
  "fechaLimitePago": "2026-10-28"
}
```

> Postman screenshots: `docs/screenshots/`.

### Health check
<img src="./screenshots/health.png" width="700"/>

### CSF — regex extraction
<img src="./screenshots/process-csf-regex.png" width="700"/>

### INE — AI extraction
<img src="./screenshots/process-ine-ai.png" width="700"/>

### Input validation (422)
<img src="./screenshots/process-validation-422.png" width="700"/>

---

## Testing

```bash
make test        # pytest inside the container
make verify      # same as CI, before pushing
make smoke       # end-to-end check (health + OCR) against the running API
make check-extraction   # real AI extraction vs samples/expected (spends AI calls)
```

`make test` and `make verify` run the same tests GitHub Actions runs on every PR and push to `main`/`develop` (`.github/workflows/tests.yml`).

---

## Technical documentation

- [docs/project/STATUS.md](./project/STATUS.md) — current phase, what works, known bugs, next step.
- [docs/project/PROJECT_PLAN.md](./project/PROJECT_PLAN.md) — vision, SOLID, patterns, architecture decisions and phased roadmap.
- [AGENTS.md](../AGENTS.md) — request lifecycle, conventions and working rules (for people and AI assistants).
- [docs/AI_WORKFLOW.en.md](./AI_WORKFLOW.en.md) — how it is developed with AI: guardrails, skills, agent and mistakes caught by the process.

---

### License

This project is not licensed for public use. All rights reserved. To request usage permissions, contact the project owner at chichohdzjesus@gmail.com.

See the full notice in [NOTICE.txt](../NOTICE.txt).
