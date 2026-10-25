# ADR 0001 — Business validation: deterministic rules in the app, AI observations as data

- **Status:** Accepted (2026-10-25, approved by the developer before any code)
- **Phase:** 4 — Business Validation (INE first, then CSF, then comprobante de domicilio)
- **Supersedes:** nothing. Formalizes the principle already stated in `PROJECT_PLAN.md` → Business Validation Layer ("AI extracts, business rules validate").

## Context

After Phase 2 the API extracts fields from INE, CSF and comprobante de domicilio. Phase 4 must answer "is this document acceptable?" with rules such as: the INE is not expired, the CURP matches the birth date, the proof of address is at most 3 months old.

Two questions had no decision:

1. **Who decides a rule:** the AI (asked to return `ine_vigente: true`), the application (Python), or both?
2. **How rules are organized** so they can be added or removed per document type without touching the pipeline.

## Options considered

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. AI decides** | The prompt asks for verdicts (`ine_vigente`, `curp_valida`) | No rule code | The model has no reliable "today" (expiration and age depend on it); verdicts change between runs and between providers (Groq vs Gemini); not unit-testable; no audit trail of *why*; prompt grows with every rule; a hallucinated `true` is indistinguishable from a real one |
| **B. App decides everything** | Python rules over extracted fields only | Deterministic, testable, same verdict for every provider, explainable | Cannot judge what only the image shows (is this actually an INE? is it legible?) |
| **C. Hybrid (chosen)** | Python rules decide; the AI may *report observations* as extracted fields (e.g. which document it sees), and rules consume them | Keeps A's only real advantage (visual judgment) without letting the AI decide; everything else as B | Observation fields must be designed as facts, not verdicts |

Evidence from this project behind the choice: Groq returned the same INE date as `DD/MM/YYYY` or ISO and the expiration as `YYYY-YYYY` or `YYYY` between runs (2026-10-25, `make check-extraction`); it also read `05/10/2026` month first. A verdict computed by the model would inherit that instability.

## Decision

1. **Rules are deterministic Python and are the only source of `valid`.** The AI never returns verdicts (`vigente`, `valido`, `true/false` about acceptability).
2. **The AI may return observations as normal extracted fields** — facts about what it sees, never judgments about acceptability. First one: `documento_detectado` (which document type the file actually is). A rule compares it with the requested `document_type`. More observations are added only when a rule needs them.
3. **Formats are stabilized before rules** (field descriptions in the prompt + normalizers in the app, as done for the comprobante): a rule never parses free-form provider output.
4. **"Today" comes from the app, in `Config.TZ`** (America/Mexico_City), and is injectable in tests. Expiration and document age are evaluated in Mexico's local date, not the server's or the model's.
5. **Validation does not change the HTTP status.** The document was processed correctly; the verdict is data. The response is `200` with a `validation` block (below). A client that needs to reject uses `validation.valid`.
6. **A missing input skips a rule instead of failing it.** The required-fields rule reports what is missing once; dependent rules return `skipped`, so one missing CURP does not produce five errors.

## Structure

```text
app/rules/
├── base_rule.py        # Rule (abstract): code, description, severity, check(fields, today) -> RuleResult
├── rule_result.py      # RuleResult: status passed | failed | skipped, message, fields involved
├── common_rules.py     # Reusable, parameterized: RequiredFields, NotExpired, MaxAge, DocumentDetected
├── ine_rules.py        # INE-specific: CurpFormat (structure + check digit), CurpMatchesBirthDate, ...
├── registry.py         # RULES_BY_DOCUMENT_TYPE = {"ine": [...], "csf": [...], "comprobante_domicilio": [...]}
└── validation_engine.py# validate(document_type, fields, today) -> validation block
```

- **Adding or removing a rule is one line in `registry.py`** (plus its test). Same pattern as `EXTRACTOR_MAP` and `PROCESSOR_MAP`: no `if document_type == ...` in the engine or the service.
- Rules work on the snake_case fields **after** `normalize_identifiers` / `normalize_dates`, before the camelCase conversion — the same place in `DocumentService` where normalization already happens.
- `severity`: `error` (makes `valid` false) or `warning` (reported, does not invalidate). Used for rules with known legitimate exceptions (e.g. name initials vs CURP, which has special cases such as `MARIA` / `JOSE` and inconvenient words).
- Each rule has a stable `code` (`ine.not_expired`) that clients can rely on; messages are human-readable and may change.

## Response

```json
"validation": {
  "valid": false,
  "checkedOn": "2026-10-25",
  "summary": {"passed": 5, "failed": 1, "warnings": 0, "skipped": 0},
  "rules": [
    {"code": "ine.not_expired", "status": "failed", "severity": "error",
     "message": "The document expired: its expiration year is before 2026.", "fields": ["fechaVencimiento"]},
    {"code": "ine.curp_matches_birth_date", "status": "passed", "severity": "error",
     "message": "CURP birth date matches fechaNacimiento.", "fields": ["curp", "fechaNacimiento"]}
  ]
}
```

- `valid` is `true` only when no rule with severity `error` failed. `skipped` rules do not invalidate by themselves (the required-fields rule already failed for that input). `summary.failed` counts failed errors; `summary.warnings` counts failed warnings.
- `checkedOn` is the local date (`Config.TZ`) the rules were evaluated against, so a stored result can be re-read later.
- `validation` is `null` when the request sends a custom `fields` list (the document as a whole cannot be judged from a subset) and for document types with no rules yet.

### Global verdict

Added after the developer's first real-INE check (2026-10-25): every rule entry was visible but there was no single answer, and a failed rule went unnoticed. `data.verdict` is always present:

```json
"verdict": {"status": "valid", "documentType": "ine", "message": "The ine document is valid: every rule passed.",
            "failedRules": [], "warnings": []}
```

| `status` | When |
|---|---|
| `valid` | No rule with severity `error` failed (warnings are listed but do not invalidate) |
| `invalid` | At least one content rule failed (expired, inconsistent CURP, not the requested document) |
| `incomplete` | Only rules that report missing data failed (`reports_missing_data`): the document can be neither confirmed nor rejected |
| `not_validated` | Custom `fields` list, or no rules for the type yet; `message` says which |
- Messages never include document values (names, CURP): only field names and the rule outcome. The values are already in `extractedFields`.

## First rule set: INE

Step 0 (format stabilization, before rules): INE field descriptions in `Config.DOCUMENT_FIELD_DESCRIPTIONS`; `fecha_nacimiento` normalized to ISO; `fecha_vencimiento` normalized to the expiration year (`YYYY`, from "VIGENCIA 2021-2031" or "2031"). Measured while implementing: with a strict "18 characters" description Groq sometimes returned the CURP as null when the OCR text had one O/0 swap, so the description asks to copy it as printed, and `recover_identifiers` fills an empty CURP / clave from the text only when exactly one candidate is valid after correction (CURP: also a correct check digit). Also from the first real INE: the OCR read the homoclave `0` (position 17) as `O`. The check digit cannot catch it (position 17 weighs 2; O = 25 and 0 = 0 differ by 50, a multiple of 10), so the CURP looked valid but encoded the wrong century and `ine.curp_matches_birth_date` failed. `resolve_curp_century` swaps O/0 there when the ISO birth date says the other century and the check digit stays valid. Implemented 2026-10-25 (`feature/ine-validation`).

| Code | Severity | Checks |
|---|---|---|
| `ine.required_fields` | error | nombre, apellido_paterno, curp, fecha_nacimiento, fecha_vencimiento, clave_elector present (apellido_materno is optional: not everyone has one) |
| `ine.document_detected` | error | The AI observation `documento_detectado` is an INE (hybrid rule) |
| `ine.curp_format` | error | CURP structure and check digit (RENAPO algorithm) |
| `ine.clave_elector_format` | error | Clave de elector structure |
| `ine.not_expired` | error | Expiration year ≥ current year in `Config.TZ` (an INE is valid through December 31 of its expiration year) |
| `ine.curp_matches_birth_date` | error | CURP date (positions 5–10) = fecha_nacimiento |
| `ine.clave_matches_curp` | error | Clave de elector birth date and sex = CURP birth date and sex |
| `ine.names_match_curp` | warning | Name initials consistent with CURP positions 1, 3 and 4 (warning: CURP has legitimate exceptions) |

CSF and comprobante de domicilio get their own tables in this ADR (or a follow-up ADR) when their turn comes; known inputs: CSF RFC/CURP consistency and `padron_status`; comprobante age ≤ 3 months using `fecha_emision`, falling back to `periodo_fin` (real CFE bills print no issue date).

## Consequences

- Same document, same verdict, whichever AI provider extracted it (as long as extraction is correct — which `make check-extraction` watches).
- Every rule is unit-tested with fictitious data and an injected date; no AI call is needed to test validation.
- The prompt only grows with observation fields, never with rule logic.
- A wrong extraction can make a valid document fail a rule. That is intended: the failure names the rule and fields, and the debug snapshot shows what the provider received.
- Rules that need real-world registries (e.g. checking a CURP against RENAPO, or an INE against the INE's online service) are out of scope: they need external APIs and credentials.
