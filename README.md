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
- **OCR con preprocesamiento**: Tesseract + OpenCV (escala de grises, contraste, reducción de ruido) + imágenes temporales para IA multimodal.
- **IA intercambiable**: `AiExtractor` con providers Gemini (imagen + texto) y Groq (solo texto).
- **Validación de entrada**: Marshmallow schemas, excepciones centralizadas, logging estructurado.
- **Contenedorización**: Docker + nginx como reverse proxy.

---

## Estado actual del proyecto

| Área | Estado | Detalle |
|------|--------|---------|
| API Flask (`health`, `documents/process`) | ✅ Estable | Endpoints funcionales con respuesta estandarizada |
| Procesamiento PDF (PyMuPDF) | ✅ Estable | Metadatos, rango de páginas, diagnóstico OCR |
| Pipeline OCR (Tesseract + OpenCV) | ✅ Estable | Preprocesamiento, temp images, cleanup |
| CSF (`extractor=regex`) | ✅ Estable | `CsfExtractor` con tests unitarios |
| INE (`extractor=ai`) | ✅ Estable | Gemini multimodal + hints CURP |
| Multi-provider AI (Gemini, Groq) | ✅ Estable | Seleccionable por request |
| Docker + nginx | ✅ Estable | `docker-compose up` |
| `comprobante_domicilio`, `estado_cuenta`, `licencia_profesional` | 🔄 Parcial | Registrados; sin extractor regex dedicado |
| Validación de reglas de negocio | 🔄 Pendiente | Capa definida conceptualmente |
| Tests de integración API / IA | 🔄 Pendiente | Solo tests unitarios de CSF |
| Procesadores Image, Excel, CSV, Word | 📋 Planificado | Arquitectura preparada, no implementados |
| Extractores regex INE, comprobante, etc. | 📋 Planificado | — |
| Providers Claude, Azure, AWS | 📋 Planificado | — |

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3.12 |
| Framework | Flask 3 |
| PDF | PyMuPDF, pdf2image |
| OCR | Tesseract, pytesseract |
| Imagen | Pillow, OpenCV |
| Validación | Marshmallow |
| IA | Google Gemini, Groq |
| Tests | pytest |
| Infra | Docker, nginx |

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
  └── YES → TesseractOcr (+ OpenCV preprocess → temp images)
  ↓
ExtractorFactory
  ├── CsfExtractor (regex)
  ├── AiExtractor → Gemini / Groq
  └── PassthroughExtractor (fallback regex)
  ↓
JSON Response (camelCase fields)
```

Documentación técnica detallada: [README_CONTEXT.md](./README_CONTEXT.md)

---

## Estructura principal del repo

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
      "reason": "sufficient_text_density",
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

> Screenshots de Postman: pendientes en `docs/screenshots/`.

---

## Testing

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar tests
pytest tests/ -v
```

Cobertura actual: tests unitarios del extractor CSF (`tests/extractors/test_csf_extractor.py`).

---

## Documentación técnica

- [README_CONTEXT.md](./README_CONTEXT.md) — visión del proyecto, SOLID, patrones, decisiones de arquitectura y estado de implementación.

---

## Roadmap breve

1. Extractores regex para INE y comprobante de domicilio
2. Capa de validación de reglas de negocio
3. Procesadores para Image, Excel, CSV, Word
4. Tests de integración API e IA
5. Providers adicionales (Claude, Azure Document Intelligence, AWS Textract)

---

### Licencia

Este proyecto no está licenciado para uso público. Todos los derechos reservados. Para obtener permisos de uso, contacta al propietario del proyecto en chichohdzjesus@gmail.com.

Consulta la licencia completa en [NOTICE.txt](./NOTICE.txt).
