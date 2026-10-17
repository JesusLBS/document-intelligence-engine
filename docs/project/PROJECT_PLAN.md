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

Examples:

* INE
* Tax documents
* Proof of address
* Bank statements
* Professional licenses
* Certifications
* Contracts
* Future document types

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
    └── YES → TesseractOcr
              ↓
              Grayscale preprocess (Pillow) → temp images (storage/temp_images)
              ↓
              OCR text + image_paths
    ↓
ExtractorFactory
    ├── CsfExtractor (regex)
    ├── AiExtractor → Gemini (multimodal: image_paths + text)
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
       Convert pages to images (pdf2image, 300 DPI)
       ↓
       Grayscale conversion (Pillow)
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

Current preprocessing before OCR: **grayscale conversion only** (Pillow, `TesseractOcr._preprocess`).

Decision history: a full OpenCV pipeline (denoise, CLAHE contrast, Otsu binarization, rotation correction) was implemented in commit `a34af13` and replaced by plain grayscale in `3182f91` (the commit that introduced `AiExtractor`); multimodal Gemini extraction, which receives the original page image, came later in `26eb3f0`. The reason for dropping the pipeline was not recorded at the time; `opencv-python`/`numpy` were later removed from `requirements.txt` because nothing imported them.

Re-introduce OpenCV only with a before/after measurement on real samples (OCR accuracy for the regex path), not by default.

---

# OCR Layer

Current implementation: `TesseractOcr` (`app/ocr/tesseract_ocr.py`)

Pipeline:

1. Convert PDF pages to images via `pdf2image` (300 DPI, poppler)
2. Convert each page to grayscale (Pillow)
3. Run Tesseract via `pytesseract` (Spanish language pack, hardcoded `spa`)
4. Save the original (non-grayscale) page images to `storage/temp_images/{request_id}/` for multimodal AI (Gemini)
5. Always delete temp images after processing. With `debug_mode=true`, the grayscale images are **additionally** saved to `storage/debug/{request_id}/`, and previous debug folders are wiped first

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

Planned regex extractors:

* INE, comprobante de domicilio, estado de cuenta, licencia profesional

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
OCR (when required) → text + image_paths
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
| Gemini | `GeminiExtractor` | Multimodal (text + page images) |
| Groq | `GroqExtractor` | Text-only |

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
* Regex extractors for INE, comprobante de domicilio, etc.
* Default fields for all registered document types

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