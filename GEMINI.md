# GEMINI.md

Las instrucciones del proyecto están en `AGENTS.md` (fuente única para todas las IAs):

@AGENTS.md

## Específico de Gemini

- Aquí no hay hooks que bloqueen `git commit` ni la lectura de `.env`: las reglas 3 y 7 de `AGENTS.md` dependen solo de ti.
- El agente `revisor-docs` (`.claude/agents/revisor-docs.md`) es un prompt: si te piden revisar la documentación, sigue su lista como checklist.
- No tienes skills: los procedimientos de `.claude/skills/<nombre>/SKILL.md` se leen y se siguen como pasos (tabla "Procedimientos" de `AGENTS.md`).
