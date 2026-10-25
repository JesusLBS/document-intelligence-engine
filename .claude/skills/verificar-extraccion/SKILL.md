---
name: verificar-extraccion
description: Verifica en vivo la extracción con IA (Groq y Gemini) contra las referencias de samples/expected con make check-extraction. Úsalo después de cambiar cualquier cosa que afecte lo que se extrae (prompt, campos o descripciones en Config, normalizadores, OCR, procesadores, proveedores de IA) y antes de dar por terminado ese cambio. No lo uses para cambios solo de documentación.
---

# Verificar extracción

Reemplaza la verificación a mano (curl por muestra, leer JSON, comparar campo por campo): un comando, una línea por muestra y proveedor. Ahorra tokens y llamadas a la IA.

## 1. Antes de correr

```bash
make ps        # app "Up (healthy)"; si no, usa /levantar-proyecto
make verify    # los tests unitarios primero: si fallan, no gastes llamadas a la IA
```

## 2. Groq primero (sin límite práctico)

```bash
make check-extraction
```

Salida:

```text
OK   comprobante_luz        groq   1.4s  15/15 (min 15)
FAIL ine                    groq   2.8s  4/5 (min 5)  differs: fecha_vencimiento
All checks passed · Gemini calls: 0
```

## 3. Gemini solo si hace falta

El plan gratuito de Gemini permite **20 peticiones por día por modelo** (ver README → Cuentas gratuitas de IA). Córrelo solo si el cambio afecta lo que recibe o devuelve Gemini (prompt, `GeminiExtractor`, `export_pages`, normalizadores), y una sola vez:

```bash
make check-extraction ARGS="--provider gemini"          # todas las muestras: 1 llamada por muestra
make check-extraction ARGS="--provider gemini --sample comprobante_luz"
```

Si responde `exceeded its quota (...)`: **no reintentes en bucle**. Repórtalo con la hora de reinicio que da el mensaje y sigue con Groq.

## 4. Leer el resultado

| Resultado | Qué hacer |
|---|---|
| Todo `OK` | Repórtalo en una línea por proveedor |
| `FAIL` con `differs: campo='valor'` | Muestra ficticia: el valor recibido está a la vista. Corre otra vez esa muestra (`--sample`): si cambia entre corridas es variación del modelo (formato sin definir → falta descripción en `Config.DOCUMENT_FIELD_DESCRIPTIONS` o un normalizador); si es estable, es una regresión del cambio |
| `FAIL` con `differs: campo` (sin valor) | Referencia con hash (la INE): **nunca** imprimas el valor. Para diagnosticar, imprime solo el formato (letras → `A`, dígitos → `9`) |
| `FAIL ... no valid response from the API` | El servidor no respondió (se recargó por un cambio en un `.py`, o está caído): `make ps` y reintenta una vez |

## 5. Referencias (`samples/expected/*.json`)

- Muestras ficticias: valores en claro. La INE de muestra: solo hashes (`{"sha256": ...}`), nunca el valor.
- Un valor puede ser una lista de alternativas válidas, o `null` si el campo debe venir vacío.
- Si un cambio **intencional** altera el formato (por ejemplo, fechas a ISO), regenera la referencia y dilo explícitamente en el reporte:

  ```bash
  docker compose exec -T app python scripts/check_extraction.py --sample ine --provider gemini --print-reference
  ```

  Gemini es la referencia porque lee el documento completo; Groq trabaja sobre texto de OCR.
- **Nunca** bajes `min_match` ni quites campos solo para que pase sin decirle al usuario por qué.
