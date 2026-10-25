# Desarrollo con IA: cómo se trabaja este proyecto

> English version: [AI_WORKFLOW.en.md](./AI_WORKFLOW.en.md)

Este proyecto se desarrolla con **Claude Code como agente de programación**. La IA escribe la mayor parte del código, los tests y la documentación; el desarrollador define la arquitectura y el alcance, revisa cada cambio, verifica con documentos reales y es el único que hace commits. Este documento explica las reglas, las barreras técnicas y el ciclo de trabajo que hacen que eso sea confiable, con enlaces a los archivos que lo implementan.

La idea central: **no se confía en que el modelo "se porte bien"**. Lo importante está forzado por código (hooks, tests, CI), y lo que no se puede forzar se verifica.

---

## 1. Contexto: una sola fuente de verdad

| Pieza | Archivo | Para qué |
|---|---|---|
| Reglas y forma de trabajo, para **cualquier** IA | [`AGENTS.md`](../AGENTS.md) | Fuente única. Codex, Cursor, Copilot y otras la leen directo |
| Adaptadores por herramienta | [`CLAUDE.md`](../CLAUDE.md), [`GEMINI.md`](../GEMINI.md) | Solo importan `AGENTS.md` y agregan lo exclusivo de su herramienta. Nunca copian reglas, porque se desincronizan |
| Estado (fase actual, qué funciona, bugs) | [`docs/project/STATUS.md`](./project/STATUS.md) | Único lugar donde se afirma el estado |
| Arquitectura, decisiones y alcance | [`docs/project/PROJECT_PLAN.md`](./project/PROJECT_PLAN.md) | El *por qué*; nunca marca avance |

Separar estado de plan evita el error más común en proyectos asistidos por IA: documentos que dicen "en progreso" algo que ya se terminó, o "listo" algo que nunca se hizo.

## 2. Barreras técnicas (no solo instrucciones)

| Regla | Mecanismo | Archivo | Probado en |
|---|---|---|---|
| La IA nunca hace commits | Hook `PreToolUse` + permiso `deny` | [`.claude/hooks/block-git-commit.sh`](../.claude/hooks/block-git-commit.sh), [`.claude/settings.json`](../.claude/settings.json) | [`tests/hooks/`](../tests/hooks/test_claude_hooks.py) |
| La IA nunca lee, edita ni busca en `.env` (API keys) | Hook `PreToolUse` sobre Read, Edit, Write, Grep, Glob y Bash; permite `.env.example` | [`.claude/hooks/block-env-access.sh`](../.claude/hooks/block-env-access.sh) | [`tests/hooks/`](../tests/hooks/test_claude_hooks.py) |
| Nadie hace push directo a `main` / `develop` | Hook de git `pre-push` | [`.githooks/pre-push`](../.githooks/pre-push) | — |
| Nada se mergea con tests en rojo | GitHub Actions en cada PR | [`.github/workflows/tests.yml`](../.github/workflows/tests.yml) | — |
| "En mi máquina pasa" no basta | `make verify` reproduce el entorno del CI (poppler y tesseract ocultos) | [`scripts/verify.sh`](../scripts/verify.sh) | — |

Las barreras de Claude Code aplican solo a Claude Code. Para otras IAs, `AGENTS.md` dice explícitamente que esas reglas dependen de ellas ([`GEMINI.md`](../GEMINI.md)).

## 3. Skills y agente: procedimientos repetibles

| Cuándo | Qué | Archivo |
|---|---|---|
| Al terminar un cambio | `/sugerir-commit`: revisa **todo** lo pendiente, arma un mapa tema → archivos y sugiere el mensaje. El desarrollador lo ejecuta | [`.claude/skills/sugerir-commit/`](../.claude/skills/sugerir-commit/SKILL.md) |
| Al levantar el entorno | `/levantar-proyecto`: diagnostica, levanta y confirma con una prueba de punta a punta | [`.claude/skills/levantar-proyecto/`](../.claude/skills/levantar-proyecto/SKILL.md) |
| Al cambiar algo que afecta la extracción | `/verificar-extraccion`: corre `make check-extraction` (muestras × proveedores contra referencias) y cuida la cuota diaria de Gemini | [`.claude/skills/verificar-extraccion/`](../.claude/skills/verificar-extraccion/SKILL.md), [`scripts/check_extraction.py`](../scripts/check_extraction.py) |
| Al cerrar una fase o antes de un PR a `main` | Agente `revisor-docs` (solo lectura): compara la documentación contra el código y entre sí | [`.claude/agents/revisor-docs.md`](../.claude/agents/revisor-docs.md) |

Los skills también ahorran tokens: un comando con salida compacta reemplaza decenas de llamadas sueltas con JSON completo.

## 4. Ciclo de trabajo

```text
Fase o tarea acordada (una a la vez, con reporte al final)
  ↓
Rama desde develop (nunca trabajo directo en main/develop)
  ↓
La IA implementa + agrega tests del comportamiento nuevo
  ↓
make verify (lo mismo que el CI)  →  make check-extraction (si cambia la extracción)
  ↓
El desarrollador verifica en Postman con documentos reales (debug_mode guarda lo que recibió cada proveedor)
  ↓
/sugerir-commit  →  el desarrollador hace el commit  →  PR  →  CI  →  merge
```

Reglas que sostienen el ciclo (todas en [`AGENTS.md`](../AGENTS.md)):

- Una fase a la vez; al terminar, la IA reporta y espera.
- Los comandos de instalación los corre el desarrollador; la IA da el comando.
- Antes de usar una librería o API externa, la IA consulta la documentación oficial, no su memoria (dos modelos de IA por defecto se apagaron en 2026 sin que el código lo notara: issue 6 de `STATUS.md`).
- Datos reales solo en la máquina del desarrollador; tests y muestras con datos ficticios ([`scripts/generate_samples.py`](../scripts/generate_samples.py)).

## 5. Errores de la IA que el proceso atrapó

La prueba de que el proceso funciona son los errores que no llegaron a `main`. Cada uno dejó un cambio en el proceso, no solo un arreglo:

| Error de la IA | Cómo se detectó | Qué cambió en el proceso |
|---|---|---|
| Reportó como arreglado un OCR que devolvía 337 caracteres de ruido | El desarrollador pidió evaluar calidad, no cantidad | `make smoke` cuenta etiquetas de la credencial, no caracteres ([issue 19](./project/STATUS.md)) |
| Cambió el puerto y el dominio local sin verificar cómo se usaban | Revisión del desarrollador | Regla en `AGENTS.md`: no cambiar dominio ni puerto sin preguntar |
| Mensajes de commit que no reflejaban todos los archivos | Revisión del desarrollador | Paso obligatorio "mapa de temas" en `/sugerir-commit` |
| Supuso que la escala de grises causaba el mal OCR | El desarrollador pidió evaluarlo | Medición de 7 variantes: la causa era el tamaño de la credencial en la hoja ([`PROJECT_PLAN.md` → Image Processing](./project/PROJECT_PLAN.md)) |
| Groq leía `05/10/2026` con el mes primero cuando se le pedían fechas ISO | Verificación en vivo | La IA devuelve la fecha impresa y la app la normaliza ([`date_normalizer.py`](../app/utils/date_normalizer.py)) |
| `debug_mode` no guardaba nada en PDFs digitales; Gemini no recibía el documento | El desarrollador probó un recibo real de CFE | Debug por petición e independiente del OCR; Gemini recibe el PDF del rango (issues 21 y 22) |
| Un 429 por cuota diaria se reportaba como "saturación" | Prueba del desarrollador | El mensaje dice qué cuota y cuándo se reinicia (issue 23) |
| Un test pasaba en Docker y fallaba en el CI | El CI del PR | `make verify` reproduce el entorno del CI (issue 24) |

## 6. Límites (para no exagerar)

- No hay CD: el despliegue no está automatizado.
- Hay un solo agente propio (`revisor-docs`), y solo se usa en momentos definidos.
- Los hooks solo protegen dentro de Claude Code; con otras herramientas, las reglas dependen de la herramienta.
- `make check-extraction` hace llamadas reales y gasta cuota: no corre en el CI.
