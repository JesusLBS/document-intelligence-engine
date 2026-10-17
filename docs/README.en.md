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
- Other registered types (`comprobante_domicilio`, `estado_cuenta`, `licencia_profesional`) work with `extractor=ai` or return empty fields with regex.

---

## Technical highlights

- **Clean architecture**: Controller → Service → Factory → Processor/Extractor, with contracts and dependency inversion.
- **Design patterns**: Strategy (processors, extractors, OCR) and Factory (dynamic selection by file and document type).
- **Smart PDF pipeline**: PyMuPDF diagnoses text density and chooses between embedded extraction or OCR.
- **OCR**: Tesseract over pages rasterized at 300 DPI and converted to grayscale, plus temporary page images for multimodal AI.
- **Interchangeable AI**: `AiExtractor` with Gemini (image + text) and Groq (text-only) providers.
- **Input validation**: Marshmallow schemas, centralized exceptions, structured logging.
- **Containerization and CI**: Docker + nginx as reverse proxy; GitHub Actions runs pytest on every PR.

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
  └── YES → TesseractOcr (grayscale → text + temp images)
  ↓
ExtractorFactory
  ├── CsfExtractor (regex)
  ├── AiExtractor → Gemini / Groq
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
│   ├── extractors/          # BaseExtractor, CsfExtractor, AiExtractor, PassthroughExtractor
│   │   └── ai/              # BaseAiExtractor, GeminiExtractor, GroqExtractor
│   ├── factories/           # DocumentProcessorFactory, ExtractorFactory
│   ├── helpers/             # ResponseHelper, Logger
│   ├── ocr/                 # BaseOcr, TesseractOcr
│   ├── processors/
│   │   ├── base/
│   │   ├── pdf/             # PdfProcessor (OCR diagnosis)
│   │   └── image/ excel/ csv/ word/ interfaces/   # empty scaffolds (planned)
│   ├── routes/              # /api/v1 blueprint
│   ├── schemas/             # Marshmallow schemas
│   ├── services/            # DocumentService (orchestrator)
│   ├── utils/               # curp_decoder, case_converter
│   └── validators/          # Request validation (decorator)
├── tests/                   # pytest
├── docs/
│   ├── project/             # PROJECT_PLAN.md (design and roadmap), STATUS.md (status)
│   ├── screenshots/         # Postman screenshots used in the README
│   └── README.en.md         # This file
├── docker/                  # Dockerfile (Python 3.12 + Tesseract + poppler)
├── nginx/                   # Reverse proxy
├── samples/                 # Sample documents with fictitious data
├── storage/                 # debug/, logs/, temp_images/ (runtime, git-ignored)
├── uploads/                 # Temporary uploads (git-ignored)
├── .github/workflows/       # CI (pytest)
├── .githooks/               # pre-push hook blocking direct pushes to main/develop
├── .claude/                 # Claude Code hook and skills
├── AGENTS.md                # Context and rules for any AI assistant
├── CLAUDE.md, GEMINI.md     # Only import AGENTS.md
├── docker-compose.yml
├── index.py                 # Flask entry point
├── requirements.txt
├── NOTICE.txt
└── .env.example
```

---

## Getting started

### Prerequisites

- Python 3.12
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) with `spa` language pack
- [poppler-utils](https://poppler.freedesktop.org/) (required by pdf2image)
- API keys (only if using `extractor=ai`): `GEMINI_API_KEY` and/or `GROQ_API_KEY`

### Local (without Docker)

```bash
git clone <repo-url>
cd document-intelligence-engine

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your AI keys if needed

python index.py
# API available at http://localhost:5000
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
# API available at http://localhost (nginx → app:5000)
```

---

## Environment variables

See [.env.example](../.env.example). Key variables:

| Variable | Description |
|----------|-------------|
| `APP_ENV` | Environment (`local`, `production`) |
| `APP_DEBUG` | Flask debug mode |
| `MAX_FILE_SIZE_MB` | Max file size (default: 10) |
| `DEFAULT_EXTRACTOR` | Default extractor (`regex` or `ai`) |
| `AI_PROVIDER` | Default AI provider (`gemini` or `groq`) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |

---

## API Endpoints

Base URL: `/api/v1`

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
| `document_type` | string | Yes | `ine`, `csf`, `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` |
| `fields` | list | No | Fields to extract (uses defaults per type if omitted) |
| `extractor` | string | No | `regex` (default) or `ai` |
| `provider` | string | No | `gemini` or `groq` (only with `extractor=ai`) |
| `force_ocr` | bool | No | Force OCR even when PDF has embedded text |
| `from_page` / `to_page` | int | No | Page range (1-indexed) |
| `all_fields` | bool | No | Extract all detectable fields (AI) |
| `include_raw_text` | bool | No | Include raw text in response (default: `true`) |
| `debug_mode` | bool | No | Save OCR images to `storage/debug` |

#### CSF example (regex)

```bash
curl -X POST http://localhost:5000/api/v1/documents/process \
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
curl -X POST http://localhost:5000/api/v1/documents/process \
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

> Postman screenshots: pending in `docs/screenshots/`.

---

## Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
pytest tests/ -v
```

The same tests run on GitHub Actions on every PR and push to `main`/`develop` (`.github/workflows/tests.yml`).

---

## Technical documentation

- [docs/project/STATUS.md](./project/STATUS.md) — current phase, what works, known bugs, next step.
- [docs/project/PROJECT_PLAN.md](./project/PROJECT_PLAN.md) — vision, SOLID, patterns, architecture decisions and phased roadmap.
- [AGENTS.md](../AGENTS.md) — request lifecycle, conventions and working rules (for people and AI assistants).

---

### License

This project is not licensed for public use. All rights reserved. To request usage permissions, contact the project owner at chichohdzjesus@gmail.com.

See the full notice in [NOTICE.txt](../NOTICE.txt).
