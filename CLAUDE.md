# CLAUDE.md

Las instrucciones del proyecto viven en `AGENTS.md` (fuente única para todas las IAs) y se importan aquí:

@AGENTS.md

## Específico de Claude Code

Solo lo que depende de Claude Code. Cualquier regla general va en `AGENTS.md`.

- **Commits**: `.claude/settings.json` + `.claude/hooks/block-git-commit.sh` bloquean `git commit` a nivel de permisos; no intentes rodearlo. Al terminar una funcionalidad, un fix o un ajuste (y de nuevo después de cada corrección), usa el skill `/sugerir-commit`.
- **Levantar el proyecto**: para "levanta / arranca / reinicia / revisa el entorno", usa el skill `/levantar-proyecto`.
- **`.env`**: `.claude/hooks/block-env-access.sh` niega leerlo, editarlo o buscar en él. Para saber con qué modelo corre la app, mira los logs (`model=...`).
- **Verificar extracción**: tras cambiar algo que afecte lo que se extrae, usa `/verificar-extraccion` (Groq primero; Gemini solo si hace falta, por su cuota diaria).
- **Al cerrar una fase o antes de un PR a `main`**: lanza el agente `revisor-docs` (solo lectura) y corrige lo que reporte.
- Para búsquedas amplias (muchos archivos), delega en un subagente Explore, así el contexto principal no se llena de lecturas.
