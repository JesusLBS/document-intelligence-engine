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
2. **No ejecutes comandos de setup ni instalación** (`pip install`, `brew install`, `make build` / `docker compose build`, crear venvs…). Da el comando exacto y qué hace; el desarrollador lo corre. Sí puedes correr los que operan el entorno ya construido: `make up`, `down`, `restart`, `ps`, `logs`, `test`, `verify`, `smoke`, `check-extraction`, `doctor`.
3. **Nunca ejecutes `git add`, `git commit`, `git push` ni abras PRs** salvo que se pida explícitamente en ese turno. Al terminar un cambio, **sugiere** el commit (procedimiento `sugerir-commit`). En Claude Code hay además un hook que lo bloquea; en las demás IAs la regla depende de ti.
4. **Nunca trabajes en `main` ni `develop`.** Si la rama actual es una de esas y la tarea modifica archivos, crea (o sugiere) una rama desde `develop` antes de escribir.
5. **Tests antes de dar por terminado:** `make verify` en verde (o `pytest tests/ -v` en el venv opcional). Si agregas comportamiento, agrega su test.
6. **Al cambiar estado del proyecto** (se termina una fase, se corrige o encuentra un bug, cambia el siguiente objetivo), actualiza `docs/project/STATUS.md`. No repitas el estado en otro archivo. Si cambias `README.md`, actualiza `docs/README.en.md` en el mismo commit (es su traducción).
7. **Sin secretos ni datos personales** en código, docs, tests o fixtures. No leas ni cites `.env` (solo `.env.example`); en Claude Code lo bloquea un hook. Los documentos de muestra y textos de test usan datos ficticios (RFC/CURP genéricos tipo `XAXX010101…`).
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
make verify        # lo mismo que el CI (poppler y tesseract ocultos con stubs, como en el runner), antes de hacer push
make smoke         # health + OCR real sobre samples/pdf/ine_sample.pdf a través de nginx (sin API keys)
make check-extraction   # extracción real con IA vs samples/expected; Groq por defecto (ver skill verificar-extraccion)
```

- Nunca sugieras `docker compose up` sin `-d`: bloquea la terminal y Ctrl+C apaga los contenedores. Usa `make up`.
- Código montado como volumen + Flask en modo debug: los cambios en `app/` se recargan solos.
- Tras cambiar `.env`, `make up` (recrea el contenedor). `make restart` **no** recarga `.env`: las variables de `env_file` se fijan al crear el contenedor (verificado).
- Un test o archivo puntual: `make test ARGS="tests/extractors/test_csf_extractor.py::TestCsfExtractor::test_extracts_rfc"`.
- Python local opcional (venv, `brew install python@3.12 tesseract tesseract-lang poppler`): `README.md` → Desarrollo local.

No hay linter/formatter configurado. CI: `.github/workflows/tests.yml` corre pytest en cada PR y push a `main`/`develop`.

## Ciclo de una petición

`app/routes/routes.py` → `@validate_process_document` (schema marshmallow en `app/schemas/process_document.py`, aplicado por `app/validators/base_validator.py`) → `DocumentController.process(validated)` (`app/controllers/document_controller.py`: recibe el dict ya deserializado por el schema, con tipos convertidos y defaults; sin lógica de negocio) → `DocumentService.process` (`app/services/document_service.py`, el orquestador real):

1. Guarda el upload en `uploads/`; la extensión decide el procesador: `DocumentProcessorFactory.make(extension)` (`app/factories/document_processor_factory.py`; `PROCESSOR_MAP` hoy solo tiene `"pdf" -> PdfProcessor`).
2. `PdfProcessor` (`app/processors/pdf/pdf_processor.py`) devuelve metadatos + diagnóstico (`diagnosis.reason`: `embedded_text_found`, `low_text_density`, `partial_text_extraction`, `scanned_image_pdf`, `text_rendered_as_paths`, `corrupt_or_proprietary_encoding`, `unknown`). Todo respeta `from_page`/`to_page`: texto, imágenes, OCR, lo que se manda a la IA y el debug. Si `processingMethod == "ocr_required"`, `force_ocr=true` o `debug_mode=true`, el procesador renderiza las páginas del rango (`processor.render_pages` → `app/processors/pdf/page_renderer.py`: pdf2image a 400 DPI → recorte a la zona con contenido, a color). Si hace falta OCR, `TesseractOcr.extract_text(pages)` (`app/ocr/tesseract_ocr.py`: pytesseract `spa` con `--psm 3` y, si la página saca menos de 30 caracteres, reintento con `--psm 11` para texto disperso, como credenciales fotografiadas) reemplaza el texto.
3. `ExtractorFactory.make(document_type, extractor_strategy, ai_provider)` (`app/factories/extractor_factory.py`): con `extractor == "ai"` siempre devuelve `AiExtractor`, sin importar el `document_type`; si no, busca en `EXTRACTOR_MAP` (hoy solo `"csf" -> CsfExtractor`) y cae en `PassthroughExtractor` (campos vacíos) para cualquier otro tipo. Sin `extractor` en el request, la estrategia sale de `Config.default_extractor_for`: `ai` para los tipos de `Config.AI_ONLY_DOCUMENT_TYPES` (`ine`, `comprobante_domicilio`: no tienen regex y `extractor=regex` responde 422 desde el schema), `DEFAULT_EXTRACTOR` para el resto. Todos los extractores se llaman igual: `extract(text, requested_fields, context)`, con un `ExtractionContext` (`app/extractors/extraction_context.py`: `document_type`, `diagnosis`, `all_fields`, `document_file`, `document_mime_type`); los de regex lo ignoran. El service nunca pregunta qué extractor concreto le tocó: si `extractor.accepts_document_file` (hoy solo Gemini, vía `AiExtractor`), exporta el documento con **solo las páginas del rango** en su formato original (`processor.export_pages`, para PDF un PDF de esas páginas) y lo pasa en `context.document_file` + `document_mime_type`; los extractores de solo texto (Groq, regex) reciben el texto embebido o del OCR.
4. `AiExtractor` (`app/extractors/ai_extractor.py`) resuelve el proveedor con su dict `providers` (`gemini` -> `GeminiExtractor`, `groq` -> `GroqExtractor`, en `app/extractors/ai/`) y agrega pistas de nombre decodificadas del CURP (`app/utils/curp_decoder.py`) si encuentra uno. El prompt compartido (`BaseAiExtractor._build_prompt`) agrega la definición de cada campo pedido desde `Config.DOCUMENT_FIELD_DESCRIPTIONS` (hoy el comprobante de domicilio). Las fechas se piden **tal como vienen impresas**, no en ISO: pedidas en ISO, Groq leyó `05/10/2026` mes primero y la app no podía detectarlo. Gemini recibe el PDF de las páginas del rango en base64 (`inline_data`, `application/pdf`; Gemini 3 lee la capa de texto y la imagen de cada página) más el texto como referencia, sea el PDF digital o escaneado; Groq solo texto. Antes Gemini solo recibía imagen cuando corría OCR: con un PDF digital (recibo de CFE) le llegaba solo el texto embebido desordenado y devolvió un campo. Ambos se llaman por HTTP con `requests`, sin SDK.
5. Los campos extraídos (snake_case) pasan por `normalize_identifiers` (`app/utils/id_normalizer.py`: corrige por posición confusiones del OCR como `O`↔`0` en CURP y clave de elector, solo si el resultado queda con estructura válida) y `normalize_dates` (`app/utils/date_normalizer.py`: fechas impresas como `14 OCT 26` o `05/10/2026` → ISO `YYYY-MM-DD`, siempre día primero; lo que no puede leer sin ambigüedad lo deja igual) y se convierten con `dict_to_camel_case` (`app/utils/case_converter.py`) y quedan en `extractedFields`.
6. Con `debug_mode=true`, `DebugStore` (`app/helpers/debug_store.py`) guarda en `storage/debug/{request_id}/`, para **cualquier** documento y con o sin OCR: `original.<ext>`, `page_<n>.png` (páginas del rango, con su número real), `sent_to_ai.<ext>` (lo que recibió Gemini), `extractor_text.txt` (el texto que recibió el extractor), `request.json` (parámetros, diagnóstico, método, qué se mandó) y `result.json`. Se guarda antes de llamar a la IA, así un proveedor que falla deja su entrada en disco. Contiene datos del documento: es local, está en `.gitignore` y se conservan las 10 carpetas más recientes. El `finally` siempre borra el upload temporal y la copia de páginas exportadas.

Campos por defecto por `document_type` (cuando no llegan `fields` ni `all_fields`): `Config.DOCUMENT_DEFAULT_FIELDS` en `app/config/__init__.py` (`ine`, `csf`, `comprobante_domicilio`, los tres tipos del proyecto; `estado_cuenta` y `licencia_profesional` se descartaron). Muestras: `samples/pdf/ine_sample.pdf` (INE pública de internet) y comprobantes ficticios generados con `docker compose exec app python scripts/generate_samples.py`.

## Extender el pipeline

- **Nuevo tipo de archivo**: implementa `DocumentProcessorInterface` (`app/contracts/document_processor_interface.py`: `process`, `render_pages`, `export_pages` y `mime_type`; para una imagen, `render_pages` devuelve la imagen y `export_pages` la copia), regístralo en `PROCESSOR_MAP` y agrega la extensión a `Config.ALLOWED_EXTENSIONS`. `app/processors/{csv,excel,image,word}/` son carpetas vacías (solo `__init__.py`), sin conectar a ninguna factory.
- **Nuevo extractor regex**: hereda de `BaseExtractor` (`app/extractors/base_extractor.py`) con la firma `extract(text, requested_fields, context=None)` y regístralo en `EXTRACTOR_MAP`. Si un tipo no tendrá regex, agrégalo a `Config.AI_ONLY_DOCUMENT_TYPES` en vez de dejar que `extractor=regex` devuelva campos vacíos.
- **Nuevo proveedor de IA**: hereda de `BaseAiExtractor` (`app/extractors/ai/base_ai_extractor.py`: el prompt es compartido en `_build_prompt`; usa `_require_api_key`, `_post_json` y `_parse_response`, que ya manejan key faltante, HTTP, timeouts y JSON inválido) y define `provider_name`; regístralo en `providers` dentro de `AiExtractor._resolve_provider` **y** en `Config.AI_PROVIDERS` (lo usa la validación del request). Agrega su config a `Config` y `.env.example`.

## Convenciones de código

- **Inglés en todo el código**: nombres, comentarios y docstrings. Docstring estilo Google en cada clase y método público (`Args:`, `Returns:`, `Raises:`), como el código existente.
- Dicts internos y de extracción en snake_case; la respuesta HTTP se convierte a camelCase **una sola vez**, en el service (`dict_to_camel_case`). No conviertas dentro de los extractores.
- Toda respuesta pasa por `ResponseHelper` (`app/helpers/response_helper.py`): `success()`, `error()`, `validation_error()` envuelven `{ok, status, message, data, meta}`. `meta.exception` solo se agrega cuando `Config.APP_ENV != "production"`.
- Request id: cada petición recibe un id (`app/helpers/request_context.py`) que aparece en `meta.request_id`, en el header `X-Request-ID`, en cada línea de log (`Logger` lo agrega solo) y en los nombres de archivos temporales e imágenes de OCR/debug. Para rastrear un reporte, busca ese id en `make logs`.
- Errores esperados: lanza una subclase de `AppException` (`app/exceptions/`) con su `status_code`; el handler (`app/exceptions/handler.py`) la responde. Los `HTTPException` de Werkzeug (404, 405, 413…) conservan su status. Cualquier otra excepción termina en 500 genérico.
- Validación de requests: decorador `validate(schema)` (`app/validators/base_validator.py`), que pasa el resultado de `schema.load()` a la ruta como `validated`. Nunca vuelvas a leer `request.form` en el controller: lo que llega es exactamente lo que validó el schema. Valores permitidos (estrategias, proveedores, tipos) viven en `Config`.
- `Config` (`app/config/__init__.py`) es la única fuente de configuración de entorno: no uses `os.getenv` disperso.
- Logging con `Logger` (`app/helpers/logger.py`) usando pares clave-valor; nunca loguees texto completo de documentos ni datos personales. Eso incluye las respuestas de la IA (traen nombres, CURP, domicilios): loguea solo longitudes, status y razones.
- Errores de proveedores de IA: `AiProviderNotConfiguredException` (503, falta la key; se lanza antes de llamar), `AiProviderException` (502; 504 en timeout; 503 con key rechazada, saturación del proveedor o cuota agotada. Un 429 nunca se reporta como saturación: `_rate_limit_reason` dice qué cuota y cuándo se reinicia). El plan gratuito de Gemini permite **20 peticiones por día por modelo**: en pruebas en vivo, gasta pocas llamadas a Gemini y prueba primero con Groq. El mensaje al cliente nunca incluye contenido del documento. Una respuesta vacía, bloqueada o que no es JSON es un error, no `{}`.
- Modelos de IA: antes de cambiar un modelo o un parámetro del payload, revisa la página de deprecaciones y la referencia oficial (Gemini: https://ai.google.dev/gemini-api/docs/deprecations · Groq: https://console.groq.com/docs/deprecations). Los dos modelos por defecto originales se apagaron en 2026 sin que el código lo notara.
- Prefiere soluciones simples a la abstracción prematura.

## Entorno

`.env` (copia de `.env.example`). Para `extractor=ai`: `GEMINI_API_KEY` y/o `GROQ_API_KEY`. Otras: `DEFAULT_EXTRACTOR` (`regex`|`ai`), `AI_PROVIDER` (`gemini`|`groq`), `GEMINI_MODEL` (default `gemini-3.6-flash`), `GEMINI_THINKING_LEVEL` (`low`; vacío para modelos sin `thinkingLevel`), `GROQ_MODEL` (default `openai/gpt-oss-120b`), `GROQ_REASONING_EFFORT` (`low`; vacío para modelos sin razonamiento), `GEMINI_TIMEOUT_SECONDS`, `GROQ_TIMEOUT_SECONDS`, `MAX_FILE_SIZE_MB`, `APP_ENV`, `LOG_LEVEL`.

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
| Cambia algo que afecta lo que se extrae (prompt, campos, normalizadores, OCR, procesadores, proveedores) | [`verificar-extraccion`](.claude/skills/verificar-extraccion/SKILL.md) |
| Se cierra una fase o se prepara un PR a `main` | Agente de solo lectura [`revisor-docs`](.claude/agents/revisor-docs.md): compara docs contra código y entre sí. Sin agentes, sigue su lista como checklist |

Barreras técnicas (Claude Code, `.claude/settings.json`): `block-git-commit.sh` niega `git commit` y `block-env-access.sh` niega leer, editar o buscar en `.env*` (no en `.env.example`). Las dos tienen tests en `tests/hooks/`. En otras IAs, esas reglas dependen de ti. Cómo encaja todo: [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md).

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
