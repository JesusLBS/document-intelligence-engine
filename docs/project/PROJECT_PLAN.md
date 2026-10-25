# Document Intelligence Engine — Project Plan

Design rationale, architecture and roadmap. This file explains **why** things are built the way they are; it does not track progress.

- Current status and next target: [`STATUS.md`](./STATUS.md) — the only place status is asserted.
- Working rules for any AI assistant (and the request lifecycle): [`AGENTS.md`](../../AGENTS.md).
- Setup, API usage and repo layout: [`README.md`](../../README.md).

---

## Project Overview

Document Intelligence Engine is a Python-based platform designed to process, analyze, validate, and extract information from multiple file types.

The initial focus is PDF processing, especially scanned PDF documents, but the architecture is intentionally designed to support future file types without modifying existing code.

The project follows SOLID principles and uses Strategy and Factory patterns to achieve extensibility, maintainability, and scalability.

The project starts as an API-first application and will be containerized using Docker from day one.

---

# Main Goal

Transform unstructured documents into structured and validated information.

Supported document types (the project scope):

* INE (voter ID)
* CSF (tax status certificate)
* Proof of address (comprobante de domicilio: electricity, water, gas, phone, internet bills)

Bank statements and professional licenses were early examples of what the platform could validate, not planned work: they were dropped from the scope (2026-10-25). The architecture still allows new types (see AGENTS.md → Extender el pipeline).

The system should be able to:

* Receive files
* Detect file type
* Validate file integrity
* Extract content
* Perform OCR when necessary
* Normalize data
* Apply business validations
* Return a structured response

---

# Why This Architecture?

The project is NOT an OCR project.

OCR is only one stage within the document processing pipeline.

The project is a Document Intelligence platform.

The architecture supports integrations such as:

* Gemini
* Groq
* OpenAI
* Claude
* Azure Document Intelligence
* AWS Textract

without requiring major architectural changes.

---

# Architecture Style

* API First
* SOLID Principles
* Strategy Pattern
* Factory Pattern
* Open/Closed Principle
* Extensible Processing Pipeline
* Future AI-Ready Architecture

---

# Technology Decisions

## Language

Python

Reason:

* Excellent ecosystem for OCR
* Excellent ecosystem for document processing
* Excellent ecosystem for AI integrations
* Mature PDF tooling
* Large community support

---

## Framework

Flask

Reason:

* Lightweight
* Easy to understand
* Fast setup
* Suitable for API-first architecture
* Ideal for MVP development

---

## Containerization

Docker

Reason:

* Environment consistency
* Avoid local dependency conflicts
* Easier onboarding
* Reproducible development environment
* Simplifies OCR-related dependencies

---

# API First Decision

The project will start as an API instead of a CLI script.

Reason:

The final output naturally becomes structured JSON.

Example:

```json
{
  "success": true,
  "fileType": "pdf",
  "isScanned": true,
  "pages": 2,
  "processingMethod": "ocr",
  "data": {},
  "errors": [],
  "warnings": []
}
```

Benefits:

* Easy Postman testing
* Future frontend integration
* Easier automation
* Better portfolio presentation
* Standardized contract

---

# SOLID Principles

## Single Responsibility Principle

Each class has a single responsibility.

Examples:

* PDF processing
* OCR processing
* Validation
* Data extraction

---

## Open/Closed Principle

The system is open for extension and closed for modification.

Future support:

* PDF
* Images
* Excel
* CSV
* Word
* Audio
* Video

without modifying existing processors.

---

## Interface Segregation Principle

Processors depend on small focused interfaces.

---

## Dependency Inversion Principle

Services depend on abstractions rather than concrete implementations.

---

# Design Patterns

## Strategy Pattern

Each file type has its own processing strategy.

Examples:

* PdfProcessor
* ImageProcessor
* ExcelProcessor
* CsvProcessor
* WordProcessor

Each processor implements:

```text
DocumentProcessorInterface
```

---

## Factory Pattern

Responsible for selecting the correct processor.

Examples:

```text
PDF   -> PdfProcessor
Image -> ImageProcessor
Excel -> ExcelProcessor
CSV   -> CsvProcessor
Word  -> WordProcessor
```

Factory:

```text
DocumentProcessorFactory
```

---

## Template Method Pattern (Optional)

Defines a standard processing lifecycle.

Example:

```text
validate()

detect()

extract()

normalize()

validateBusinessRules()

buildResponse()
```

All processors follow the same lifecycle.

---

# Application Architecture

```text
Client
    ↓
API Endpoint
    ↓
Controller
    ↓
DocumentService
    ↓
DocumentProcessorFactory
    ↓
DocumentProcessorInterface
    ↓
Selected Processor (PdfProcessor)
    ↓
Diagnosis (OCR required?)
    ├── NO  → Embedded text extraction
    └── YES → render requested pages (400 DPI, cropped to content, color) → TesseractOcr → OCR text
    ↓
ExtractorFactory
    ├── CsfExtractor (regex)
    ├── AiExtractor → Gemini (PDF of the requested pages, inline base64 + text)
    │              → Groq (text-only)
    └── PassthroughExtractor (regex fallback)
    ↓
Validator (planned)
    ↓
Response Builder (camelCase fields)
    ↓
JSON Response
```

---

# Layer Responsibilities

## Controllers

Responsibilities:

* Receive requests
* Validate input
* Call services
* Return responses

---

## Services

Responsibilities:

* Orchestrate processing flow
* Coordinate processors
* Build responses

---

## Factories

Responsibilities:

* Resolve implementations dynamically

Examples:

* DocumentProcessorFactory
* ExtractorFactory

---

## Processors

Responsibilities:

* Execute document-specific logic

Examples:

* PdfProcessor
* ImageProcessor
* ExcelProcessor

---

## Extractors

Responsibilities:

* Convert raw content into structured data

Examples:

* RegexExtractor
* AI-based extractors

---

## Validators

Responsibilities:

* Apply business rules
* Verify extracted information

---

## OCR

Responsibilities:

* Extract text from images

Examples:

* Tesseract
* PaddleOCR

---

## Contracts

Responsibilities:

* Shared interfaces
* Abstractions
* Application contracts

---

# Initial MVP

PDF-only. The MVP answers:

* Is the file a valid PDF?
* Does it contain embedded text?
* Is it scanned / does it require OCR?
* How many pages does it have?
* What fields can be extracted for the given document type?

Flow:

```text
PDF
 ↓
PdfProcessor (PyMuPDF)
 ↓
Diagnosis (text density, scan detection)
 ├── Sufficient text → Extract embedded text
 └── OCR required (or force_ocr=true)
       ↓
       Convert pages to images (pdf2image, 400 DPI)
       ↓
       Crop to the content area, keeping color (Pillow)
       ↓
       Tesseract OCR + temp images for AI
       ↓
ExtractorFactory (regex / ai)
       ↓
Structured JSON Response
```

---

# PDF Processing

Libraries:

* PyMuPDF
* pdf2image

Responsibilities:

* Open PDF
* Count pages
* Detect embedded text
* Convert pages into images

---

# Image Processing

Current preprocessing before OCR: **crop to the content area, in color** (Pillow, `page_renderer.crop_to_content`). No grayscale, no binarization: Tesseract binarizes internally.

Decision history: a full OpenCV pipeline (denoise, CLAHE contrast, Otsu binarization, rotation correction) was implemented in commit `a34af13` and replaced by plain grayscale in `3182f91` (the commit that introduced `AiExtractor`); multimodal Gemini extraction, which receives the original page image, came later in `26eb3f0`. The reason for dropping the pipeline was not recorded at the time; `opencv-python`/`numpy` were later removed from `requirements.txt` because nothing imported them.

Measurement (2026-10-25, `samples/pdf/ine_sample.pdf`: a color INE photo on a white letter page). Each variant was scored by INE labels and ID patterns found in the OCR text (max 14), and by how many fields a text-only AI (Groq) extracted from that text:

| Variant | Score | Groq fields |
|---|---|---|
| Full page, grayscale, 300 DPI (previous pipeline) | 0–3 | 0/7 |
| Full page, color | 0–5 | — |
| Cropped to content, grayscale, 300 DPI | 9 | 4/7 matching Gemini |
| **Cropped to content, color, 400 DPI** (chosen) | **10** | 5–6/7 matching Gemini |

Conclusions: grayscale was not the cause (with the full page, color and grayscale were equally bad); the real problem was the small card on a mostly white page defeating Tesseract's layout analysis. Cropping fixed it; color was slightly better than grayscale; 400 DPI cost about +0.4 s per page. The remaining errors were look-alike characters in structured IDs (e.g. `O` read for `0`), now corrected by position in `app/utils/id_normalizer.py`.

Re-introduce OpenCV (deskew, perspective correction for skewed photos) only with the same kind of before/after measurement, not by default.

---

# OCR Layer

Current implementation: `TesseractOcr` (`app/ocr/tesseract_ocr.py`)

Pipeline:

1. The processor renders the requested pages (`render_pages` → `app/processors/pdf/page_renderer.py`): `pdf2image` at 400 DPI (poppler)
2. Crop each page to its content area, keeping color (Pillow); see Image Processing for the measurement
3. Run Tesseract via `pytesseract` (Spanish language pack, hardcoded `spa`) with `--psm 3` (automatic layout); if a page yields fewer than 30 characters, retry with `--psm 11` (sparse text) and keep the longer result. Reason: PSM 3 returned 0 characters on a photographed INE placed on a page, PSM 11 returned 337 (measured 2026-10-17 on `samples/pdf/ine_sample.pdf`)
4. Rendered pages are independent of OCR: `debug_mode=true` also renders them for digital PDFs, and `DebugStore` saves them with the upload, what each extractor received and the result in `storage/debug/{request_id}/` (last 10 kept)

Gemini does not get these crops: it gets the PDF of the requested pages (`export_pages`) and reads its text layer and page images natively (up to 50 MB inline, ~258 tokens per page). Until 2026-10-25 it only got images when OCR ran, so a digital bill reached it as out-of-order embedded text and it returned one field. Measured after the change on the INE sample: 7/7 fields, identical on 3 runs (the crop is no longer needed for Gemini).

Future option:

* PaddleOCR

Responsibilities:

* Extract text from scanned PDF pages
* Generate page images for AI multimodal extraction
* Support page range (`from_page`, `to_page`) and debug mode

---

# Data Extraction

Current extractors (via `ExtractorFactory`):

| Extractor | Strategy | Document types | Notes |
|-----------|----------|----------------|-------|
| `CsfExtractor` | regex | `csf` | Pure regex over embedded/OCR text |
| `AiExtractor` | ai | any registered type | Delegates to Gemini or Groq |
| `PassthroughExtractor` | regex fallback | types without dedicated regex extractor | Returns empty fields, never raises |

`AiExtractor` delegates to provider-specific classes:

* `GeminiExtractor` — multimodal (text + page images from OCR pipeline)
* `GroqExtractor` — text-only

For INE documents, `AiExtractor` enriches prompts with CURP decoding hints via `app/utils/curp_decoder.py`.

Regex approach (initial):

* Pattern matching for structured fields: RFC, CURP, names, dates, tax regimes

Regex is only planned where the layout is fixed (CSF). INE (photographed cards) and proof of address (one bill format per provider) are AI-only (`Config.AI_ONLY_DOCUMENT_TYPES`): they default to `extractor=ai` and `extractor=regex` is rejected with 422.

AI output is made uniform across providers by the app, not by the prompt alone:

* `Config.DOCUMENT_FIELD_DESCRIPTIONS` — meaning and format of each field, added to the shared prompt.
* Dates are requested exactly as printed and converted to ISO by `app/utils/date_normalizer.py` (day first). Asked for ISO directly, Groq read `05/10/2026` month first (`2026-05-10`), an error the app cannot detect afterwards.
* `app/utils/id_normalizer.py` — OCR look-alike fixes in CURP and clave de elector.

---

# Business Validation Layer

Examples:

* Document age <= 3 months
* Name matches doctor information
* Valid tax regime
* Valid expiration date
* Required fields present

Important:

AI extracts.

Business rules validate.

Validation logic must always remain inside the application.

---

# AI Integration

AI extraction goes through `AiExtractor` and the Strategy pattern for providers.

Current flow:

```text
PDF
 ↓
OCR (when required) → text; PDF of the requested pages for providers that read documents
 ↓
AiExtractor (BaseExtractor)
 ↓
Provider (gemini | groq)
 ↓
Structured fields (camelCase)
 ↓
Response
```

Implemented providers:

| Provider | Class | Capabilities |
|----------|-------|--------------|
| Gemini | `GeminiExtractor` | Multimodal (text + page images). Default `gemini-3.6-flash`, `thinkingLevel: low`, JSON mode, temperature left at default (Gemini 3 guidance) |
| Groq | `GroqExtractor` | Text-only. Default `openai/gpt-oss-120b` (reasoning model: `reasoning_effort: low`, `include_reasoning: false`), JSON mode |

Provider selection: configurable per request (`provider` form field) or via `AI_PROVIDER` env var.

Abstraction:

```text
BaseExtractor
    ├── CsfExtractor (regex)
    ├── AiExtractor
    │     └── BaseAiExtractor
    │           ├── GeminiExtractor
    │           └── GroqExtractor
    └── PassthroughExtractor
```

Planned providers:

* OpenAI
* Claude
* Azure Document Intelligence
* AWS Textract

---

# Folder Structure

The current repository tree lives in [`README.md`](../../README.md) → "Estructura del repo" (single copy, to avoid drift).

Planned additions (not yet present):

* Real processors in `app/processors/{image,excel,csv,word}/` (today they are empty scaffold folders with `__init__.py` only)
* `app/validators/` business-rule validators (today the folder only holds request validation)
* Dedicated regex extractors for INE, comprobante de domicilio, etc.
* `docs/diagrams/`

---

# Dependencies

Exact pinned versions: `requirements.txt`.

API

* Flask
* marshmallow (request validation)

PDF

* PyMuPDF
* pdf2image (requires poppler on the host)

Images

* Pillow

OCR

* pytesseract (requires Tesseract + `spa` language pack on the host)

AI providers

* requests (Gemini and Groq are called over plain HTTP, no vendor SDK)

Utilities

* python-dotenv

Tests

* pytest

---

# Project Roadmap

Scope of each phase. Which phase is done, in progress or next: [`STATUS.md`](./STATUS.md) — never mark progress here.

## Phase 1 — Core Platform

* Docker Environment
* Flask API (`/health`, `/documents/process`)
* PDF Processor with OCR diagnosis
* OCR Integration (Tesseract)
* Strategy Pattern + Factory Pattern
* Standard Response Structure
* Marshmallow validation + centralized exceptions

## Phase 2 — Data Extraction

* CSF regex extractor with unit tests
* AI extraction (Gemini multimodal, Groq text-only)
* CURP decoder hints for INE
* Proof of address via AI: default fields, field descriptions in the prompt, ISO date normalization
* Default fields for all registered document types (INE, CSF, proof of address)

## Phase 3 — File Processors

* Image Processor
* Excel Processor
* CSV Processor
* Word Processor

## Phase 4 — Business Validation

* Business Validation Engine
* Document age rules, field cross-validation, required fields

## Phase 5 — AI Providers

* Gemini (multimodal)
* Groq (text-only)
* OpenAI, Claude, Azure Document Intelligence, AWS Textract

## Phase 6 — Quality & Observability

* CI (GitHub Actions running pytest on every PR)
* Service, factory and API tests (mocked OCR and AI providers)
* Postman collection + screenshots
* Advanced Document Intelligence Features

---

# Portfolio Objective

The goal is not to build a simple OCR application.

The goal is to build a scalable, extensible, and maintainable Document Intelligence platform capable of processing, validating, and extracting information from multiple document formats while following professional software architecture practices.

The project should demonstrate:

* SOLID Principles
* Strategy Pattern
* Factory Pattern
* API Design
* OCR Integration
* Document Processing
* Extensible Architecture
* AI Integration (Gemini, Groq)
* Multimodal Document Extraction