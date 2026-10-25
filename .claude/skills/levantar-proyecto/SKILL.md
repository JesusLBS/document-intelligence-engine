---
name: levantar-proyecto
description: Úsalo cuando el usuario pida levantar, arrancar, iniciar, reiniciar o revisar el entorno de document-intelligence-engine. Revisa qué está corriendo y los requisitos; si todo pasa, levanta directo con make up y confirma con make smoke; si falta algo, dice exactamente qué falta y da el comando.
---

# Levantar el proyecto

Docker es el entorno principal. Todo pasa por el `Makefile` (la lógica está en `scripts/`).

## 1. ¿Ya está arriba?

```bash
make ps
```

- Si `app` está `Up (healthy)` y `web` está `Up`: avisa que ya está arriba, da la URL (`http://document-intelligence.test/api/v1/health`) y **no hagas nada más**, salvo que el usuario haya pedido reiniciar (`make restart`).
- Si no hay contenedores o están detenidos: sigue al paso 2.

## 2. Requisitos

```bash
make doctor
```

Para Docker hacen falta en `OK`: `docker`, `docker-daemon`, `docker-compose`, `env-file` y `hosts`. `port-80` no debe decir `WARN`. Las líneas de "Local venv" son opcionales: ignóralas salvo que el usuario pida correr sin Docker.

## 3. Según el resultado

### Todo pasa

No preguntes más; corre directo:

```bash
make up      # segundo plano + espera el healthcheck
make smoke   # health + OCR real sobre el PDF de muestra
```

Reporta la URL y el resultado del smoke. Si la imagen no existe todavía o el usuario cambió `requirements.txt` o el `Dockerfile`, hace falta `make build`: **dale el comando**, no lo corras tú (regla 2 de `AGENTS.md`).

### Falta algo

No instales ni arranques nada de lo que falta (regla 2 de `AGENTS.md`). Por cada línea `MISSING` o `WARN`:

| Línea | Qué decir |
|---|---|
| `docker-daemon: MISSING` | Abrir Docker Desktop |
| `env-file: MISSING` | `cp .env.example .env` (y agregar claves de IA si va a usar `extractor=ai`) |
| `hosts: MISSING` | Agregar `127.0.0.1 document-intelligence.test` a `/etc/hosts` (requiere sudo: dale el comando) |
| `port-80: WARN` | Otro proceso ocupa el 80 (el mensaje trae el `lsof`); casi siempre es otro proyecto que quedó arriba: apagarlo. **No** cambies el puerto de este proyecto |
| `git-hooks: WARN` | `git config core.hooksPath .githooks` (no bloquea levantar) |

Cuando el usuario lo resuelva, vuelve a correr `make doctor` y sigue con "Todo pasa".

## Nunca

- `docker compose up` sin `-d` (bloquea la terminal; Ctrl+C apaga los contenedores).
- Leer o citar `.env`.
