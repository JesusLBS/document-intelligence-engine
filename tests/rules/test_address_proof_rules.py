from datetime import date

import pytest

from app.rules.validation_engine import build_verdict, validate

TODAY = date(2026, 11, 1)

# Fictitious bill (same values as samples/pdf/comprobante_luz_sample.pdf), dates already normalized.
BILL = {
    "nombre_titular": "XAVIER EJEMPLO PRUEBA",
    "domicilio_completo": "AV DE LOS EJEMPLOS 123 INT 4, COL. CENTRO, CUAUHTEMOC, CIUDAD DE MEXICO, C.P. 06000",
    "calle": "AV DE LOS EJEMPLOS",
    "numero_exterior": "123",
    "numero_interior": "4",
    "colonia": "CENTRO",
    "municipio": "CUAUHTEMOC",
    "estado": "CIUDAD DE MEXICO",
    "codigo_postal": "06000",
    "proveedor": "ENERGIA DEL VALLE S.A. DE C.V.",
    "tipo_servicio": "luz",
    "numero_servicio": "000123456789",
    "fecha_emision": "2026-10-14",
    "periodo_inicio": "2026-08-12",
    "periodo_fin": "2026-10-13",
    "fecha_limite_pago": "2026-10-28",
    "documento_detectado": "comprobante_domicilio",
}


def run(today: date = TODAY, **changes) -> dict:
    return validate("comprobante_domicilio", {**BILL, **changes}, today=today)


def rule(result: dict, code: str) -> dict:
    return next(entry for entry in result["rules"] if entry["code"] == code)


def verdict(result: dict) -> dict:
    return build_verdict("comprobante_domicilio", result, "unused")


class TestValidBill:
    def test_every_rule_passes(self):
        result = run()

        assert result["summary"] == {"passed": 7, "failed": 0, "warnings": 0, "skipped": 0}
        assert verdict(result)["status"] == "valid"

    def test_optional_address_parts_may_be_missing(self):
        result = run(numero_exterior=None, numero_interior=None, municipio=None, estado=None)

        assert verdict(result)["status"] == "valid"


class TestMaxAge:
    def test_cfe_bill_without_issue_date_uses_the_period_end(self):
        # Real CFE bills print no issue date: the billed period end is the reference.
        entry = rule(run(fecha_emision=None), "comprobante.max_age")

        assert (entry["status"], entry["fields"]) == ("passed", ["periodoFin"])

    def test_issue_date_wins_over_the_period_end(self):
        entry = rule(run(fecha_emision="2026-10-14", periodo_fin="2026-01-01"), "comprobante.max_age")

        assert (entry["status"], entry["fields"]) == ("passed", ["fechaEmision"])

    @pytest.mark.parametrize("dated, outcome", [
        ("2026-08-01", "passed"),   # exactly 3 months
        ("2026-07-31", "failed"),   # one day older
        ("2026-11-02", "failed"),   # future
    ])
    def test_three_month_window(self, dated, outcome):
        assert rule(run(fecha_emision=dated), "comprobante.max_age")["status"] == outcome

    def test_payment_due_date_is_not_a_fallback(self):
        # Only the due date: age cannot be measured, so the bill is incomplete, never accepted.
        result = run(fecha_emision=None, periodo_fin=None, fecha_limite_pago="2026-10-28")

        assert rule(result, "comprobante.date_present")["status"] == "failed"
        assert rule(result, "comprobante.max_age")["status"] == "skipped"
        assert verdict(result)["status"] == "incomplete"

    def test_old_bill_is_invalid(self):
        result = run(fecha_emision=None, periodo_inicio="2026-03-01", periodo_fin="2026-04-30",
                     fecha_limite_pago="2026-05-15")

        assert verdict(result)["status"] == "invalid"
        assert verdict(result)["failedRules"] == ["comprobante.max_age"]


class TestRequiredFields:
    def test_missing_postal_code_is_incomplete(self):
        result = run(codigo_postal=None)

        assert rule(result, "comprobante.required_fields")["fields"] == ["codigoPostal"]
        assert rule(result, "comprobante.postal_code_format")["status"] == "skipped"
        assert verdict(result)["status"] == "incomplete"


class TestPostalCode:
    @pytest.mark.parametrize("postal_code, outcome", [
        ("06000", "passed"), ("99999", "passed"), (" 03100 ", "passed"),
        ("6000", "failed"), ("00500", "failed"), ("0600A", "failed"),
    ])
    def test_five_digits_in_the_mexican_range(self, postal_code, outcome):
        assert rule(run(codigo_postal=postal_code), "comprobante.postal_code_format")["status"] == outcome


class TestWarnings:
    def test_service_type_otro_is_a_warning(self):
        result = run(tipo_servicio="otro")

        entry = rule(result, "comprobante.service_type_known")
        assert (entry["status"], entry["severity"]) == ("failed", "warning")
        assert verdict(result)["status"] == "valid"

    def test_period_out_of_order_is_a_warning(self):
        # e.g. day and month swapped by a misread: the end comes before the start.
        result = run(periodo_inicio="2026-12-08", periodo_fin="2026-10-13")

        assert rule(result, "comprobante.period_consistent")["status"] == "failed"
        assert verdict(result)["warnings"] == ["comprobante.period_consistent"]

    def test_due_date_before_the_period_end_is_a_warning(self):
        assert rule(run(fecha_limite_pago="2026-10-01"), "comprobante.period_consistent")["status"] == "failed"

    def test_period_check_needs_two_dates(self):
        result = run(periodo_inicio=None, fecha_limite_pago=None)

        assert rule(result, "comprobante.period_consistent")["status"] == "skipped"


class TestDocumentDetected:
    def test_an_ine_sent_as_a_bill_is_invalid(self):
        result = run(documento_detectado="ine")

        assert verdict(result)["status"] == "invalid"
        assert verdict(result)["failedRules"] == ["comprobante.document_detected"]


class TestPrivacy:
    def test_messages_never_include_document_values(self):
        result = run(codigo_postal="00500", periodo_inicio="2026-12-08", fecha_emision="2025-01-10")
        messages = " ".join(entry["message"] for entry in result["rules"])

        for value in ("XAVIER", "00500", "2026-12-08", "2025-01-10", "AV DE LOS EJEMPLOS"):
            assert value not in messages
