# AGENTS.md

Contexto base para **cualquier** asistente de IA (Claude Code, Codex/ChatGPT, Gemini, Cursor, Copilot, Windsurf…) y para cualquier persona que abra este repo por primera vez. Es la **fuente única**: `CLAUDE.md` y `GEMINI.md` lo importan y solo agregan lo específico de su herramienta. Si una regla aplica sin importar la IA, va **aquí**, no en un archivo de herramienta.

## Qué es

`document-intelligence-engine`: API Flask (un solo servicio Python, no es monorepo) que convierte PDFs (nativos o escaneados) en JSON estructurado. Diagnostica si hace falta OCR, lo corre cuando hace falta y extrae campos por regex o con un proveedor de IA intercambiable (Gemini, Groq). Proyecto de portafolio personal.

## Al empezar una sesión (en este orden)

1. Este archivo completo.
2. [`docs/project/STATUS.md`](docs/project/STATUS.md) — en qué fase va el proyecto, qué funciona, bugs abiertos y qué sigue.
3. [`docs/project/PROJECT_PLAN.md`](docs/project/PROJECT_PLAN.md) — solo la sección que pida la tarea (razonamiento de arquitectura, alcance de una fase). Antes de un cambio de arquitectura, léelo completo.
4. Solo el código que pida la tarea (tabla "Dónde está qué"). No recorras el repo si el doc ya responde.

### Jerarquía de fuentes

| Tema | Fuente de verdad |
|---|---|
| Cómo trabajar en el repo (reglas, flujo, git, ciclo de una petición) | **`AGENTS.md`** (este archivo) |
| Fase actual, qué funciona, bugs abiertos, qué sigue | `docs/project/STATUS.md` |
| Arquitectura, patrones, decisiones y alcance de cada fase | `docs/project/PROJECT_PLAN.md` |
| Levantar el proyecto, API (ejemplos curl), árbol del repo | `README.md` (`docs/README.en.md` es su traducción) |

`CLAUDE.md` y `GEMINI.md` **no** pueden contradecir este archivo. Si encuentras una contradicción entre fuentes, o entre un doc y el código, no elijas una: señálala y pregunta.

## ⚠️ Reglas (obligatorias para cualquier IA)

1. **Una fase o tarea a la vez.** Implementa solo lo pedido; al terminar, reporta y espera la siguiente instrucción.
2. **No ejecutes comandos de setup ni instalación** (`pip install`, `brew install`, `make build` / `docker compose build`, crear venvs…). Da el comando exacto y qué hace; el desarrollador lo corre. Sí puedes correr los que operan el entorno ya construido: `make up`, `down`, `restart`, `ps`, `logs`, `test`, `verify`, `smoke`, `doctor`.
3. **Nunca ejecutes `git add`, `git commit`, `git push` ni abras PRs** salvo que se pida explícitamente en ese turno. Al terminar un cambio, **sugiere** el commit (procedimiento `sugerir-commit`). En Claude Code hay además un hook que lo bloquea; en las demás IAs la regla depende de ti.
4. **Nunca trabajes en `main` ni `develop`.** Si la rama actual es una de esas y la tarea modifica archivos, crea (o sugiere) una rama desde `develop` antes de escribir.
5. **Tests antes de dar por terminado:** `make verify` en verde (o `pytest tests/ -v` en el venv opcional). Si agregas comportamiento, agrega su test.
6. **Al cambiar estado del proyecto** (se termina una fase, se corrige o encuentra un bug, cambia el siguiente objetivo), actualiza `docs/project/STATUS.md`. No repitas el estado en otro archivo. Si cambias `README.md`, actualiza `docs/README.en.md` en el mismo commit (es su traducción).
7. **Sin secretos ni datos personales** en código, docs, tests o fixtures. No leas ni cites `.env` (solo `.env.example`). Los documentos de muestra y textos de test usan datos ficticios (RFC/CURP genéricos tipo `XAXX010101…`).
8. Cambios mínimos y localizados: no reformatees ni refactorices archivos ajenos a la tarea.
9. **Antes de inferir cómo se usa una librería o API externa** (Flask, marshmallow, PyMuPDF, Gemini, Groq…), revisa su documentación oficial (fetch/búsqueda, no de memoria). Si no la consultaste, dilo.

## Stack y comandos

Python 3.12, fijado en `.python-version` (lo usan el CI y pyenv/uv si los tienes; el Dockerfile repite `3.12` a mano). El código usa sintaxis `X | None`, requiere ≥ 3.10: el Python 3.9 del sistema macOS **no** sirve · Flask 3 · marshmallow · PyMuPDF · pdf2image · pytesseract · Pillow · requests · pytest · Docker + nginx. Versiones exactas: `requirements.txt`.

**Docker es el entorno principal** (trae Python 3.12, Tesseract `spa` y poppler; nginx en el puerto 80 atiende `http://document-intelligence.test`, dominio local declarado en `/etc/hosts` y en el `server_name` de `nginx/default.conf`. Nunca cambies ese dominio ni el puerto sin pedirlo: el desarrollador trabaja con dominios `.test`, no con `localhost`). El Python local es opcional y en la Mac del desarrollador hoy no tiene los requisitos: no asumas que existe. Los comandos son atajos del `Makefile`; la lógica vive en `scripts/`.

```bash
make doctor        # requisitos de la máquina, .env, /etc/hosts, puerto 80 y hooks (solo lee)
make up            # levanta en segundo plano y espera el healthcheck (no ocupa la terminal)
make build         # igual, reconstruyendo la imagen: solo si cambian requirements.txt o el Dockerfile
make down | restart | ps | logs | shell
make test          # pytest dentro del contenedor; filtrar: make test ARGS="-k csf"
make verify        # lo mismo que el CI, antes de hacer push
make smoke         # health + OCR real sobre samples/pdf/ine_sample.pdf a través de nginx (sin API keys)
```

- Nunca sugieras `docker compose up` sin `-d`: bloquea la terminal y Ctrl+C apaga los contenedores. Usa `make up`.
- Código montado como volumen + Flask en modo debug: los cambios en `app/` se recargan solos.
- Un test o archivo puntual: `make test ARGS="tests/extractors/test_csf_extractor.py::TestCsfExtractor::test_extracts_rfc"`.
- Python local opcional (venv, `brew install python@3.12 tesseract tesseract-lang poppler`): `README.md` → Desarrollo local.

No hay linter/formatter configurado. CI: `.github/workflows/tests.yml` corre pytest en cada PR y push a `main`/`develop`.

## Ciclo de una petición

`app/routes/routes.py` → `@validate_process_document` (schema marshmallow en `app/schemas/process_document.py`, aplicado por `app/validators/base_validator.py`) → `DocumentController.process` (`app/controllers/document_controller.py`: lee los campos del form, sin lógica de negocio) → `DocumentService.process` (`app/services/document_service.py`, el orquestador real):

1. Guarda el upload en `uploads/`; la extensión decide el procesador: `DocumentProcessorFactory.make(extension)` (`app/factories/document_processor_factory.py`; `PROCESSOR_MAP` hoy solo tiene `"pdf" -> PdfProcessor`).
2. `PdfProcessor` (`app/processors/pdf/pdf_processor.py`) devuelve metadatos + diagnóstico (`diagnosis.reason`: `embedded_text_found`, `low_text_density`, `partial_text_extraction`, `scanned_image_pdf`, `text_rendered_as_paths`, `corrupt_or_proprietary_encoding`, `unknown`). Si `processingMethod == "ocr_required"` o `force_ocr=true`, corre `TesseractOcr.extract_text(...)` (`app/ocr/tesseract_ocr.py`: pdf2image a 300 DPI → escala de grises con Pillow → pytesseract `spa`) y guarda las imágenes originales de cada página en `storage/temp_images/{request_id}/` para la IA multimodal.
3. `ExtractorFactory.make(document_type, extractor_strategy, ai_provider)` (`app/factories/extractor_factory.py`): con `extractor == "ai"` siempre devuelve `AiExtractor`, sin importar el `document_type`; si no, busca en `EXTRACTOR_MAP` (hoy solo `"csf" -> CsfExtractor`) y cae en `PassthroughExtractor` (campos vacíos) para cualquier otro tipo.
4. `AiExtractor` (`app/extractors/ai_extractor.py`) resuelve el proveedor con su dict `providers` (`gemini` -> `GeminiExtractor`, `groq` -> `GroqExtractor`, en `app/extractors/ai/`) y agrega pistas de nombre decodificadas del CURP (`app/utils/curp_decoder.py`) si encuentra uno. Gemini recibe `image_paths` (multimodal); Groq solo texto. Ambos se llaman por HTTP con `requests`, sin SDK.
5. Los campos extraídos (snake_case) se convierten con `dict_to_camel_case` (`app/utils/case_converter.py`) y quedan en `extractedFields`.
6. El `finally` siempre borra el upload temporal y, si corrió OCR, las imágenes temporales (`TesseractOcr.cleanup_temp_images`). Con `debug_mode=true` las imágenes en escala de grises se guardan **además** en `storage/debug/{request_id}/` (y antes se borran las carpetas de debug anteriores).

Campos por defecto por `document_type` (cuando no llegan `fields` ni `all_fields`): `Config.DOCUMENT_DEFAULT_FIELDS` en `app/config/__init__.py` (hoy solo `ine`, `csf`, `comprobante_domicilio`).

## Extender el pipeline

- **Nuevo tipo de archivo**: implementa `DocumentProcessorInterface` (`app/contracts/document_processor_interface.py`), regístralo en `PROCESSOR_MAP` y agrega la extensión a `Config.ALLOWED_EXTENSIONS`. `app/processors/{csv,excel,image,word,interfaces}/` son carpetas vacías (solo `__init__.py`), sin conectar a ninguna factory.
- **Nuevo extractor regex**: hereda de `BaseExtractor` (`app/extractors/base_extractor.py`) y regístralo en `EXTRACTOR_MAP`. Mientras no exista, un `document_type` registrado en `Config.DOCUMENT_TYPES` sin extractor devuelve campos vacíos con `extractor=regex`.
- **Nuevo proveedor de IA**: hereda de `BaseAiExtractor` (`app/extractors/ai/base_ai_extractor.py`; el prompt es compartido en `_build_prompt`) y regístralo en `providers` dentro de `AiExtractor._resolve_provider`. Agrega su config a `Config` y `.env.example`.

## Convenciones de código

- **Inglés en todo el código**: nombres, comentarios y docstrings. Docstring estilo Google en cada clase y método público (`Args:`, `Returns:`, `Raises:`), como el código existente.
- Dicts internos y de extracción en snake_case; la respuesta HTTP se convierte a camelCase **una sola vez**, en el service (`dict_to_camel_case`). No conviertas dentro de los extractores.
- Toda respuesta pasa por `ResponseHelper` (`app/helpers/response_helper.py`): `success()`, `error()`, `validation_error()` envuelven `{ok, status, message, data, meta}`. `meta.exception` solo se agrega fuera de `production`.
- Errores esperados: lanza una subclase de `AppException` (`app/exceptions/`) con su `status_code`; el handler (`app/exceptions/handler.py`) la responde. Cualquier otra excepción termina en 500 genérico.
- `Config` (`app/config/__init__.py`) es la única fuente de configuración de entorno: no uses `os.getenv` disperso.
- Logging con `Logger` (`app/helpers/logger.py`) usando pares clave-valor; nunca loguees texto completo de documentos ni datos personales.
- Prefiere soluciones simples a la abstracción prematura.

## Entorno

`.env` (copia de `.env.example`). Para `extractor=ai`: `GEMINI_API_KEY` y/o `GROQ_API_KEY`. Otras: `DEFAULT_EXTRACTOR` (`regex`|`ai`), `AI_PROVIDER` (`gemini`|`groq`), `GEMINI_MODEL`, `GROQ_MODEL`, `MAX_FILE_SIZE_MB`, `APP_ENV`, `LOG_LEVEL`.

## Dónde está qué

| Necesito… | Ir a |
|---|---|
| En qué fase va, qué sigue, bugs abiertos | `docs/project/STATUS.md` |
| Por qué la arquitectura es así, alcance de cada fase | `docs/project/PROJECT_PLAN.md` |
| Parámetros del endpoint y ejemplos de respuesta | `README.md` → API Endpoints |
| Validación de entrada | `app/schemas/process_document.py`, `app/validators/` |
| Orquestación | `app/services/document_service.py` |
| Diagnóstico de PDF / OCR | `app/processors/pdf/pdf_processor.py`, `app/ocr/tesseract_ocr.py` |
| Extractores y proveedores de IA | `app/extractors/`, `app/extractors/ai/` |
| Configuración | `app/config/__init__.py`, `.env.example` |
| Infra y entorno local | `docker/Dockerfile`, `docker-compose.yml`, `nginx/default.conf`, `Makefile`, `scripts/` |
| Levantar, comandos, problemas comunes | `README.md` → Desarrollo local |
| CI | `.github/workflows/tests.yml` |

## Procedimientos (para cualquier IA)

Viven en `.claude/skills/<nombre>/SKILL.md`. Claude Code los usa como skills; **si tu herramienta no tiene skills, abre el archivo y sigue sus pasos** (lo que diga "Claude" aplica a ti).

| Cuando… | Procedimiento |
|---|---|
| Se termina una funcionalidad, fix o ajuste, o se pide un commit | [`sugerir-commit`](.claude/skills/sugerir-commit/SKILL.md) |
| Se pide levantar, arrancar, reiniciar o revisar el entorno | [`levantar-proyecto`](.claude/skills/levantar-proyecto/SKILL.md) |

## Git

### Ramas

- **`main`** (estable) y **`develop`** (integración) están protegidas: **nunca** reciben commit ni push directo, de nadie.
- Todo trabajo ocurre en una rama creada desde `develop`: `feature/<nombre>`, `fix/<nombre>`, `docs/<nombre>`, `chore/<nombre>`, `test/<nombre>` (mismo vocabulario que los tipos de commit), y vuelve vía PR.
- Promoción: rama → PR a `develop` → PR `develop` → `main`. Sin rama `qa`: es un proyecto de un solo desarrollador sin ambiente de QA.
- Red local: `.githooks/pre-push` bloquea el push directo a `main`/`develop`. Se activa una vez por clon con `git config core.hooksPath .githooks`. No sustituye la protección de rama en GitHub.

### Commits

Conventional Commits + gitmoji, en inglés, como el historial del repo:

```
<type>: :<gitmoji>: <subject en minúsculas, imperativo, sin punto final>

<description: una línea>
```

- Header y description **≤ 100 caracteres cada uno**. Tipos: `feat :sparkles:`, `fix :bug:`, `refactor :recycle:`, `docs :memo:`, `test :white_check_mark:`, `chore :wrench:`, `ci :construction_worker:`, `perf :zap:`, `style :art:`.
- El mensaje cubre **todo** lo pendiente en el working tree; si hay cambios sin relación, sugiere varios commits. Sin líneas `Co-Authored-By`: el desarrollador es el único autor.

## Cómo responder

Español, directo, sin relleno. El código y los commits, en inglés. Si falta contexto, pregunta antes de asumir; no inventes una implementación: lee el archivo.

## Archivos por herramienta

| Herramienta | Qué lee de forma automática | Qué hacemos |
|---|---|---|
| Codex / ChatGPT, Cursor, Copilot, Windsurf | `AGENTS.md` | Nada extra |
| Claude Code | `CLAUDE.md` | `CLAUDE.md` importa este archivo con `@AGENTS.md` |
| Gemini CLI / Code Assist | `GEMINI.md` | `GEMINI.md` importa este archivo con `@AGENTS.md` |

Al agregar una herramienta nueva: si lee `AGENTS.md`, no crees nada; si no, crea su archivo con **solo** un import o referencia a `AGENTS.md` más lo exclusivo de esa herramienta. Nunca copies reglas: se desincronizan.
