# CLAUDE.md

Las instrucciones del proyecto viven en `AGENTS.md` (fuente única para todas las IAs) y se importan aquí:

@AGENTS.md

## Específico de Claude Code

Solo lo que depende de Claude Code. Cualquier regla general va en `AGENTS.md`.

- **Commits**: `.claude/settings.json` + `.claude/hooks/block-git-commit.sh` bloquean `git commit` a nivel de permisos; no intentes rodearlo. Al terminar una funcionalidad, un fix o un ajuste (y de nuevo después de cada corrección), usa el skill `/sugerir-commit`.
- Para búsquedas amplias (muchos archivos), delega en un subagente Explore, así el contexto principal no se llena de lecturas.
