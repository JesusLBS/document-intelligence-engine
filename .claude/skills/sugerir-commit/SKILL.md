---
name: sugerir-commit
description: Sugiere el mensaje de commit (Conventional Commits + gitmoji, inglés, header y description ≤100 caracteres) que cubra TODO lo pendiente en el working tree, con la lista de archivos de cada commit. Máximo 2–3 commits, prefiriendo menos. Úsalo siempre al terminar una funcionalidad, un fix o un ajuste, cuando el usuario pida un commit, o después de corregir algo sobre un commit ya sugerido. Nunca ejecuta el commit.
---

# Sugerir commit

**Nunca hagas `git add` ni `git commit`**: solo sugiere y el desarrollador lo ejecuta a mano. En Claude Code, `.claude/settings.json` + `.claude/hooks/block-git-commit.sh` bloquean el commit a nivel de permisos.

## 1. Revisa TODO lo pendiente (obligatorio, siempre)

No escribas el mensaje de memoria ni solo con el último cambio de la conversación. Si después de sugerir un commit se corrigió algo, repite esta revisión y sugiere de nuevo.

```bash
git status --short
git diff --stat            # sin stage
git diff --cached --stat   # en stage (ojo: un git mv deja el renombre ya en stage)
git diff                   # contenido, si el --stat no basta
```

- Incluye archivos nuevos (`??`), modificados y los que ya están en stage.
- Commits locales ya hechos y sin push no se mezclan: el mensaje describe solo lo pendiente.
- Señala archivos que **no** deban ir: `.env`, credenciales, `uploads/`, `storage/`, PDFs reales con datos personales, `.DS_Store`.

## 2. ¿Cuántos commits?

- **Por defecto, uno.** Si hay dos temas y uno es pequeño, un solo commit que mencione ambos está bien.
- Divide solo cuando valga la pena (por ejemplo, poder revertir un cambio de runtime/Docker sin tocar docs). **Máximo 2–3 por sesión.** No dividas por tipo de archivo porque sí.
- Si sugieres más de uno, para **cada** commit da: la lista de archivos, su `git add` exacto y su `git commit`. Si ya hay cambios en stage, indica el **orden** en que deben hacerse para que nada se cuele en el commit equivocado. Di en una línea por qué conviene dividir, y ofrece la alternativa de un solo commit.

## 3. Formato

```
<type>: :<gitmoji>: <subject>

<description>
```

| Regla | Detalle |
|---|---|
| Idioma | Inglés (como el historial del repo) |
| Header | ≤ 100 caracteres |
| `subject` | Minúsculas, imperativo (`add`, `fix`, `align`), sin punto final |
| `description` | Una sola línea, ≤ 100 caracteres, sin viñetas. Explica el qué o el porqué principal |
| Autoría | Sin `Co-Authored-By`: el desarrollador es el único autor |

| type | gitmoji | Cuándo |
|---|---|---|
| `feat` | `:sparkles:` | Funcionalidad nueva |
| `fix` | `:bug:` | Corrección de un bug |
| `refactor` | `:recycle:` | Reestructura sin cambiar comportamiento |
| `docs` | `:memo:` | Solo documentación |
| `test` | `:white_check_mark:` | Solo tests |
| `chore` | `:wrench:` | Config, tooling, dependencias, Docker |
| `ci` | `:construction_worker:` | Workflows de CI |
| `perf` | `:zap:` | Rendimiento |
| `style` | `:art:` | Formato sin cambios de lógica |

## 4. Cuenta los caracteres

```bash
printf '%s' 'feat: :sparkles: add business validation layer for csf' | wc -m
```

Si algo pasa de 100, acórtalo; no lo partas en varias líneas.

## 5. Entrega

Por cada commit:

1. Tabla o lista de archivos que incluye.
2. El bloque listo para copiar en zsh:

```zsh
git add <archivo1> <archivo2>
git commit -m "<header>" -m "<description>"
```

3. El conteo: `header 59/100 · description 81/100`.

**No lo ejecutes.**
