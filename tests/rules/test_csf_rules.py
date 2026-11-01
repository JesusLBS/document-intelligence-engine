from datetime import date

import pytest

from app.rules.common_rules import months_before
from app.rules.csf_rules import rfc_check_digit
from app.rules.validation_engine import build_verdict, validate
from app.utils.id_normalizer import derive_tipo_persona

TODAY = date(2026, 10, 31)

# Fictitious taxpayers; RFC and CURP check digits computed with their algorithms.
FISICA = {
    "rfc": "PELJ900515AB7",
    "curp": "PELJ900515HDFRPN07",
    "full_name": "JUAN PEREZ LOPEZ",
    "padron_status": "ACTIVO",
    "tax_regimes": ["Régimen de Sueldos y Salarios"],
    "issued_at": "2026-10-15",
    "documento_detectado": "csf",
}
MORAL = {
    "rfc": "ABC200101XY3",
    "curp": None,
    "full_name": "EMPRESA EJEMPLO SA DE CV",
    "padron_status": "ACTIVO",
    "tax_regimes": ["Régimen General de Ley Personas Morales"],
    "issued_at": "2026-10-15",
    "documento_detectado": "csf",
}


def run(base: dict = FISICA, today: date = TODAY, **changes) -> dict:
    """Validate a CSF the way the service does: tipo_persona is derived from the RFC first."""
    return validate("csf", derive_tipo_persona({**base, **changes}), today=today)


def rule(result: dict, code: str) -> dict:
    return next(entry for entry in result["rules"] if entry["code"] == code)


def verdict(result: dict) -> dict:
    return build_verdict("csf", result, "unused")


class TestValidCsf:
    def test_persona_fisica_passes_every_rule(self):
        result = run()

        assert result["summary"] == {"passed": 10, "failed": 0, "warnings": 0, "skipped": 0}
        assert verdict(result)["status"] == "valid"

    def test_persona_moral_skips_the_curp_rules_as_not_applicable(self):
        result = run(MORAL)

        for code in ("csf.curp_required", "csf.curp_format", "csf.rfc_matches_curp"):
            entry = rule(result, code)
            assert (entry["status"], entry["message"]) == ("skipped", "Not applicable to a persona moral.")
        assert result["summary"] == {"passed": 7, "failed": 0, "warnings": 0, "skipped": 3}
        assert verdict(result)["status"] == "valid"


class TestTipoPersona:
    @pytest.mark.parametrize("rfc, tipo", [
        ("PELJ900515AB7", "fisica"),
        ("ABC200101XY3", "moral"),
        ("PELJ-900515-AB7", "fisica"),
        ("PELJ90", None),
        (None, None),
    ])
    def test_derived_from_the_rfc_length(self, rfc, tipo):
        assert derive_tipo_persona({"rfc": rfc})["tipo_persona"] == tipo

    def test_only_added_when_there_is_an_rfc(self):
        assert derive_tipo_persona({"curp": "X"}) == {"curp": "X"}


class TestRfc:
    def test_published_example_has_a_valid_check_digit(self):
        # Independent check of the algorithm: the widely published example RFC ends in 8.
        assert rfc_check_digit("GODE561231GR") == "8"

    @pytest.mark.parametrize("rfc", ["PELJ900515AB", "PE1J900515AB7", "PELJ901315AB7", "AB200101XY3"])
    def test_bad_structure_or_date_fails(self, rfc):
        assert rule(run(rfc=rfc), "csf.rfc_format")["status"] == "failed"

    def test_spaces_hyphens_and_case_are_tolerated(self):
        assert rule(run(rfc="pelj-900515 ab7"), "csf.rfc_format")["status"] == "passed"

    def test_wrong_check_digit_is_only_a_warning(self):
        result = run(rfc="PELJ900515AB8")

        entry = rule(result, "csf.rfc_check_digit")
        assert (entry["status"], entry["severity"]) == ("failed", "warning")
        assert verdict(result)["status"] == "valid"
        assert verdict(result)["warnings"] == ["csf.rfc_check_digit"]

    @pytest.mark.parametrize("rfc", ["XAXX010101000", "XEXX010101000"])
    def test_generic_rfcs_are_invalid(self, rfc):
        result = run(rfc=rfc, curp=None)

        assert rule(result, "csf.rfc_not_generic")["status"] == "failed"
        assert verdict(result)["status"] == "invalid"


class TestCurpForPersonaFisica:
    def test_missing_curp_is_incomplete_and_dependent_rules_are_skipped(self):
        result = run(curp=None)

        assert rule(result, "csf.curp_required")["status"] == "failed"
        assert rule(result, "csf.curp_format")["status"] == "skipped"
        assert rule(result, "csf.rfc_matches_curp")["status"] == "skipped"
        assert verdict(result)["status"] == "incomplete"

    def test_rfc_and_curp_with_different_birth_dates_are_invalid(self):
        from app.utils.id_normalizer import curp_check_digit

        curp = "PELJ900516HDFRPN0"
        result = run(curp=curp + curp_check_digit(curp))

        assert rule(result, "csf.curp_format")["status"] == "passed"
        assert rule(result, "csf.rfc_matches_curp")["status"] == "failed"
        assert verdict(result)["status"] == "invalid"


class TestPadron:
    @pytest.mark.parametrize("status, outcome", [("ACTIVO", "passed"), (" activo ", "passed"),
                                                 ("SUSPENDIDO", "failed"), ("CANCELADO", "failed")])
    def test_only_activo_passes(self, status, outcome):
        assert rule(run(padron_status=status), "csf.padron_active")["status"] == outcome


class TestMaxAge:
    """At most 3 calendar months old on Mexico's calendar, and never in the future."""

    @pytest.mark.parametrize("issued, outcome", [
        ("2026-10-31", "passed"),   # today
        ("2026-07-31", "passed"),   # exactly 3 months
        ("2026-07-30", "failed"),   # one day older
        ("2026-11-01", "failed"),   # future
    ])
    def test_three_month_window(self, issued, outcome):
        assert rule(run(issued_at=issued), "csf.max_age")["status"] == outcome

    def test_date_not_normalized_fails_with_a_clear_message(self):
        entry = rule(run(issued_at="15 DE MAYO"), "csf.max_age")

        assert entry["status"] == "failed"
        assert "YYYY-MM-DD" in entry["message"]

    @pytest.mark.parametrize("today, oldest", [
        (date(2026, 5, 31), date(2026, 2, 28)),   # clamped to February's last day
        (date(2028, 5, 31), date(2028, 2, 29)),   # leap year
        (date(2026, 1, 15), date(2025, 10, 15)),  # crosses the year
    ])
    def test_months_before_handles_month_ends_and_years(self, today, oldest):
        assert months_before(today, 3) == oldest

    def test_old_csf_is_invalid(self):
        result = run(issued_at="2025-05-15")

        assert verdict(result)["status"] == "invalid"
        assert verdict(result)["failedRules"] == ["csf.max_age"]


class TestDocumentDetected:
    def test_another_document_is_invalid(self):
        result = run(documento_detectado="ine")

        assert rule(result, "csf.document_detected")["status"] == "failed"
        assert verdict(result)["status"] == "invalid"


class TestPrivacy:
    def test_messages_never_include_document_values(self):
        result = run(rfc="PELJ900515AB8", padron_status="SUSPENDIDO", issued_at="2025-05-15")
        messages = " ".join(entry["message"] for entry in result["rules"])

        for value in ("PELJ900515AB8", "PELJ900515HDFRPN07", "JUAN PEREZ LOPEZ", "2025-05-15", "SUSPENDIDO"):
            assert value not in messages
