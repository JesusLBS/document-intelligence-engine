from app.rules.common_rules import DocumentDetected, MaxAge, NotExpired, OnlyForPersonaFisica, RequiredFields
from app.rules.csf_rules import PadronActive, RfcCheckDigit, RfcFormat, RfcMatchesCurp, RfcNotGeneric
from app.rules.ine_rules import ClaveElectorFormat, ClaveMatchesCurp, CurpFormat, CurpMatchesBirthDate, NamesMatchCurp

# Rules per document type, in report order. Adding or removing a rule is one line here (plus its
# test); the engine and the service never branch on document_type (docs/decisions/0001).
RULES_BY_DOCUMENT_TYPE = {
    "ine": [
        # apellido_materno is optional: not everyone has a second surname.
        RequiredFields("ine.required_fields", (
            "nombre", "apellido_paterno", "curp", "fecha_nacimiento", "fecha_vencimiento", "clave_elector",
        )),
        DocumentDetected("ine.document_detected", expected="ine"),
        CurpFormat(),
        ClaveElectorFormat(),
        NotExpired("ine.not_expired", year_field="fecha_vencimiento"),
        CurpMatchesBirthDate(),
        ClaveMatchesCurp(),
        NamesMatchCurp(),
    ],
    # Persona física (13-character RFC, has a CURP) and moral (12, no CURP): CURP rules are
    # "not applicable" for a moral. tipo_persona is derived from the RFC by the app.
    "csf": [
        RequiredFields("csf.required_fields", ("rfc", "full_name", "padron_status", "issued_at")),
        DocumentDetected("csf.document_detected", expected="csf"),
        RfcFormat(),
        RfcCheckDigit(),
        RfcNotGeneric(),
        OnlyForPersonaFisica(RequiredFields("csf.curp_required", ("curp",))),
        OnlyForPersonaFisica(CurpFormat("csf.curp_format")),
        OnlyForPersonaFisica(RfcMatchesCurp()),
        PadronActive(),
        MaxAge("csf.max_age", date_fields=("issued_at",), months=3),
    ],
}
