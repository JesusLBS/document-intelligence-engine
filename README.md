# Document Intelligence Engine

> Versión en inglés: [docs/README.en.md](./docs/README.en.md)

## Desarrollado por: Jesus Chicho Hernández

API Python/Flask de procesamiento documental con IA, patrones de diseño y arquitectura limpia. Proyecto de portafolio que demuestra cómo transformar documentos no estructurados (PDF) en datos estructurados mediante un pipeline extensible: diagnóstico OCR, extracción regex o IA, y respuesta JSON estandarizada.

No es un script OCR aislado: es una plataforma de inteligencia documental donde OCR, extractores y proveedores de IA son capas intercambiables.

---

## ¿Qué resuelve este proyecto?

Recibe documentos PDF (nativos o escaneados), analiza su contenido, decide si requiere OCR, extrae campos relevantes según el tipo de documento y devuelve una respuesta estructurada lista para integrarse en flujos de validación o automatización.

Casos de uso actuales:

- **CSF** (Constancia de Situación Fiscal): extracción regex de RFC, CURP, nombre, régimen fiscal, etc.
- **INE**: extracción vía IA con hints de CURP y soporte multimodal (Gemini).
- Otros tipos registrados (`comprobante_domicilio`, `estado_cuenta`, `licencia_profesional`) funcionan con `extractor=ai` o devuelven campos vacíos con regex.

---

## Highlights técnicos

- **Arquitectura limpia**: Controller → Service → Factory → Processor/Extractor, con contratos e inversión de dependencias.
- **Patrones de diseño**: Strategy (procesadores, extractores, OCR) y Factory (selección dinámica por tipo de archivo y documento).
- **Pipeline PDF inteligente**: PyMuPDF diagnostica densidad de texto y decide entre extracción embebida u OCR.
- **OCR**: Tesseract sobre páginas rasterizadas a 300 DPI y convertidas a escala de grises, más imágenes temporales de cada página para IA multimodal.
- **IA intercambiable**: `AiExtractor` con providers Gemini (imagen + texto) y Groq (solo texto).
- **Validación de entrada**: Marshmallow schemas, excepciones centralizadas, logging estructurado.
- **Contenedorización y CI**: Docker + nginx como reverse proxy; GitHub Actions corre pytest en cada PR.

---

## Estado del proyecto

Fase actual, qué funciona hoy, bugs conocidos y siguiente paso: **[docs/project/STATUS.md](./docs/project/STATUS.md)** (única fuente de estado).

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.12 |
| Framework | Flask 3 |
| PDF | PyMuPDF, pdf2image |
| OCR | Tesseract, pytesseract |
| Imagen | Pillow |
| Validación | Marshmallow |
| IA | Google Gemini, Groq (HTTP con `requests`) |
| Tests | pytest |
| Infra | Docker, nginx, GitHub Actions |

---

## Arquitectura

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
  └── YES → TesseractOcr (escala de grises → texto + temp images)
  ↓
ExtractorFactory
  ├── CsfExtractor (regex)
  ├── AiExtractor → Gemini / Groq
  └── PassthroughExtractor (fallback regex)
  ↓
JSON Response (camelCase fields)
```

Diseño, patrones y decisiones de arquitectura: [docs/project/PROJECT_PLAN.md](./docs/project/PROJECT_PLAN.md)

---

## Estructura del repo

```text
document-intelligence-engine/
├── app/
│   ├── config/              # Config (única fuente de variables de entorno) + logging
│   ├── contracts/           # DocumentProcessorInterface
│   ├── controllers/         # DocumentController (sin lógica de negocio)
│   ├── exceptions/          # AppException + handler global
│   ├── extractors/          # BaseExtractor, CsfExtractor, AiExtractor, PassthroughExtractor
│   │   └── ai/              # BaseAiExtractor, GeminiExtractor, GroqExtractor
│   ├── factories/           # DocumentProcessorFactory, ExtractorFactory
│   ├── helpers/             # ResponseHelper, Logger
│   ├── ocr/                 # BaseOcr, TesseractOcr
│   ├── processors/
│   │   ├── base/
│   │   ├── pdf/             # PdfProcessor (diagnóstico OCR)
│   │   └── image/ excel/ csv/ word/ interfaces/   # scaffolds vacíos (planificados)
│   ├── routes/              # Blueprint /api/v1
│   ├── schemas/             # Schemas marshmallow
│   ├── services/            # DocumentService (orquestador)
│   ├── utils/               # curp_decoder, case_converter
│   └── validators/          # Validación de request (decorador)
├── tests/                   # pytest
├── docs/
│   ├── project/             # PROJECT_PLAN.md (diseño y roadmap), STATUS.md (estado)
│   ├── screenshots/         # Capturas de Postman usadas en este README
│   └── README.en.md         # Este README en inglés
├── docker/                  # Dockerfile (Python 3.12 + Tesseract + poppler)
├── nginx/                   # Reverse proxy
├── samples/                 # Documentos de muestra con datos ficticios
├── storage/                 # debug/, logs/, temp_images/ (generados en runtime, ignorados por git)
├── uploads/                 # Uploads temporales (ignorados por git)
├── .github/workflows/       # CI (pytest)
├── .githooks/               # pre-push que bloquea push directo a main/develop
├── .claude/                 # Hook y skills de Claude Code
├── AGENTS.md                # Contexto y reglas para cualquier asistente de IA
├── CLAUDE.md, GEMINI.md     # Solo importan AGENTS.md
├── docker-compose.yml
├── index.py                 # Entry point Flask
├── requirements.txt
├── NOTICE.txt
└── .env.example
```

---

## Instrucciones de inicio

### Requisitos previos

- Python 3.12
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) con paquete de idioma `spa`
- [poppler-utils](https://poppler.freedesktop.org/) (requerido por pdf2image)
- Claves de API (solo si usas `extractor=ai`): `GEMINI_API_KEY` y/o `GROQ_API_KEY`

### Local sin Docker

```bash
git clone <repo-url>
cd document-intelligence-engine

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edita .env con tus claves de IA si aplica

python index.py
# API disponible en http://localhost:5000
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
# API disponible en http://localhost (nginx → app:5000)
```

---

## Variables de entorno

Consulta [.env.example](./.env.example). Variables principales:

| Variable | Descripción |
|----------|-------------|
| `APP_ENV` | Entorno (`local`, `production`) |
| `APP_DEBUG` | Modo debug Flask |
| `MAX_FILE_SIZE_MB` | Tamaño máximo de archivo (default: 10) |
| `DEFAULT_EXTRACTOR` | Extractor por defecto (`regex` o `ai`) |
| `AI_PROVIDER` | Provider IA por defecto (`gemini` o `groq`) |
| `GEMINI_API_KEY` | Clave API de Google Gemini |
| `GROQ_API_KEY` | Clave API de Groq |

---

## API Endpoints

Base URL: `/api/v1`

### GET /health

Verifica que el servicio esté activo.

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

Procesa un documento PDF y extrae campos según tipo y estrategia.

**Content-Type:** `multipart/form-data`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `file` | file | Sí | PDF (máx. 10 MB) |
| `document_type` | string | Sí | `ine`, `csf`, `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` |
| `fields` | list | No | Campos a extraer (usa defaults por tipo si se omite) |
| `extractor` | string | No | `regex` (default) o `ai` |
| `provider` | string | No | `gemini` o `groq` (solo con `extractor=ai`) |
| `force_ocr` | bool | No | Forzar OCR aunque el PDF tenga texto embebido |
| `from_page` / `to_page` | int | No | Rango de páginas (1-indexed) |
| `all_fields` | bool | No | Extraer todos los campos detectables (IA) |
| `include_raw_text` | bool | No | Incluir texto crudo en respuesta (default: `true`) |
| `debug_mode` | bool | No | Guardar imágenes OCR en `storage/debug` |

#### Ejemplo CSF (regex)

```bash
curl -X POST http://localhost:5000/api/v1/documents/process \
  -F "file=@csf.pdf" \
  -F "document_type=csf" \
  -F "extractor=regex" \
  -F "fields=rfc" \
  -F "fields=curp" \
  -F "fields=full_name"
```

**Response (parcial):**

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

#### Ejemplo INE (ai + gemini)

```bash
curl -X POST http://localhost:5000/api/v1/documents/process \
  -F "file=@ine.pdf" \
  -F "document_type=ine" \
  -F "extractor=ai" \
  -F "provider=gemini" \
  -F "include_raw_text=false"
```

**Response (parcial):**

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

> Screenshots de Postman:  `docs/screenshots/`.

### Health check
<img src="./docs/screenshots/health.png" width="700"/>

### CSF — extracción regex
<img src="./docs/screenshots/process-csf-regex.png" width="700"/>

### INE — extracción con IA
<img src="./docs/screenshots/process-ine-ai.png" width="700"/>

### Validación de entrada (422)
<img src="./docs/screenshots/process-validation-422.png" width="700"/>

---

## Testing

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar tests
pytest tests/ -v
```

Los mismos tests corren en GitHub Actions en cada PR y push a `main`/`develop` (`.github/workflows/tests.yml`).

---

## Documentación técnica

- [docs/project/STATUS.md](./docs/project/STATUS.md) — fase actual, qué funciona, bugs conocidos, siguiente paso.
- [docs/project/PROJECT_PLAN.md](./docs/project/PROJECT_PLAN.md) — visión, SOLID, patrones, decisiones de arquitectura y roadmap por fases.
- [AGENTS.md](./AGENTS.md) — ciclo de una petición, convenciones y reglas de trabajo (para personas y asistentes de IA).

---

### Licencia

Este proyecto no está licenciado para uso público. Todos los derechos reservados. Para obtener permisos de uso, contacta al propietario del proyecto en chichohdzjesus@gmail.com.

Consulta la licencia completa en [NOTICE.txt](./NOTICE.txt).
