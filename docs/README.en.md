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
- **OCR with preprocessing**: Tesseract + OpenCV (grayscale, contrast, noise reduction) + temporary images for multimodal AI.
- **Interchangeable AI**: `AiExtractor` with Gemini (image + text) and Groq (text-only) providers.
- **Input validation**: Marshmallow schemas, centralized exceptions, structured logging.
- **Containerization**: Docker + nginx as reverse proxy.

---

## Current project status

| Area | Status | Detail |
|------|--------|--------|
| Flask API (`health`, `documents/process`) | ✅ Stable | Functional endpoints with standardized response |
| PDF processing (PyMuPDF) | ✅ Stable | Metadata, page range, OCR diagnosis |
| OCR pipeline (Tesseract + OpenCV) | ✅ Stable | Preprocessing, temp images, cleanup |
| CSF (`extractor=regex`) | ✅ Stable | `CsfExtractor` with unit tests |
| INE (`extractor=ai`) | ✅ Stable | Gemini multimodal + CURP hints |
| Multi-provider AI (Gemini, Groq) | ✅ Stable | Selectable per request |
| Docker + nginx | ✅ Stable | `docker compose up` |
| `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` | 🔄 Partial | Registered; no dedicated regex extractor |
| Business rule validation | 🔄 Pending | Conceptually defined layer |
| API / AI integration tests | 🔄 Pending | CSF unit tests only |
| Image, Excel, CSV, Word processors | 📋 Planned | Architecture ready, not implemented |
| INE, proof-of-address regex extractors | 📋 Planned | — |

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Framework | Flask 3 |
| PDF | PyMuPDF, pdf2image |
| OCR | Tesseract, pytesseract |
| Image | Pillow, OpenCV |
| Validation | Marshmallow |
| AI | Google Gemini, Groq |
| Tests | pytest |
| Infra | Docker, nginx |

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
  └── YES → TesseractOcr (+ OpenCV preprocess → temp images)
  ↓
ExtractorFactory
  ├── CsfExtractor (regex)
  ├── AiExtractor → Gemini / Groq
  └── PassthroughExtractor (regex fallback)
  ↓
JSON Response (camelCase fields)
```

Detailed technical documentation: [README_CONTEXT.md](../README_CONTEXT.md)

---

## Main repo structure

```text
document-intelligence-engine/
├── app/
│   ├── config/
│   ├── contracts/
│   ├── controllers/
│   ├── exceptions/
│   ├── extractors/
│   │   └── ai/              # gemini_extractor, groq_extractor, base_ai_extractor
│   ├── factories/
│   ├── helpers/
│   ├── ocr/
│   ├── processors/
│   │   ├── base/
│   │   └── pdf/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   ├── utils/               # curp_decoder, case_converter
│   └── validators/
├── docker/
├── nginx/
├── storage/
│   ├── debug/
│   ├── logs/
│   └── temp_images/
├── tests/
│   └── extractors/
├── docs/
│   └── README.en.md
├── docker-compose.yml
├── index.py
├── requirements.txt
├── README.md
├── README_CONTEXT.md
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
      "reason": "sufficient_text_density",
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

Current coverage: CSF extractor unit tests (`tests/extractors/test_csf_extractor.py`).

---

## Technical documentation

- [README_CONTEXT.md](../README_CONTEXT.md) — project vision, SOLID, patterns, architecture decisions, and implementation status.

---

## Brief roadmap

1. Regex extractors for INE and proof of address
2. Business rule validation layer
3. Processors for Image, Excel, CSV, Word
4. API and AI integration tests
5. Additional providers (Claude, Azure Document Intelligence, AWS Textract)

---

### License

This project is not licensed for public use. All rights reserved. To request usage permissions, contact the project owner at chichohdzjesus@gmail.com.

See the full notice in [NOTICE.txt](../NOTICE.txt).
