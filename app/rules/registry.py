from app.rules.common_rules import DocumentDetected, NotExpired, RequiredFields
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
}
