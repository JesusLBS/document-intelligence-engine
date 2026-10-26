from datetime import date, datetime, timezone

import pytest

from app.rules import validation_engine
from app.utils.id_normalizer import curp_check_digit
from app.rules.registry import RULES_BY_DOCUMENT_TYPE
from app.rules.validation_engine import local_today, validate

TODAY = date(2026, 10, 25)

# Fictitious person; CURP check digit computed with the RENAPO algorithm.
VALID_INE = {
    "nombre": "JUAN",
    "apellido_paterno": "PEREZ",
    "apellido_materno": "LOPEZ",
    "curp": "PELJ900515HDFRPN07",
    "fecha_nacimiento": "1990-05-15",
    "fecha_vencimiento": "2031",
    "clave_elector": "PRLPJN90051509H000",
    "documento_detectado": "ine",
}


def run(**changes) -> dict:
    """Validate VALID_INE with some fields changed (None removes a field's value)."""
    return validate("ine", {**VALID_INE, **changes}, today=TODAY)


def rule(result: dict, code: str) -> dict:
    return next(entry for entry in result["rules"] if entry["code"] == code)


class TestValidIne:
    def test_every_rule_passes(self):
        result = run()

        assert result["valid"] is True
        assert result["checkedOn"] == "2026-10-25"
        assert result["summary"] == {"passed": 8, "failed": 0, "warnings": 0, "skipped": 0}
        assert {entry["status"] for entry in result["rules"]} == {"passed"}

    def test_fields_are_reported_in_camel_case(self):
        assert rule(run(), "ine.curp_matches_birth_date")["fields"] == ["curp", "fechaNacimiento"]


class TestCurpFormat:
    def test_published_illustrative_curp_has_a_valid_check_digit(self):
        # Independent check of the algorithm: the widely published example CURP ends in 4.
        assert curp_check_digit("HEGG560427MVZRRL04") == "4"

    def test_wrong_check_digit_fails(self):
        assert rule(run(curp="PELJ900515HDFRPN08"), "ine.curp_format")["status"] == "failed"

    @pytest.mark.parametrize("curp", ["PELJ900515HDFRPN0", "PELJ900515QDFRPN07", "PEL1900515HDFRPN07"])
    def test_bad_structure_fails(self, curp):
        assert rule(run(curp=curp), "ine.curp_format")["status"] == "failed"

    def test_impossible_birth_date_fails(self):
        curp = "PELJ901315HDFRPN0"
        assert rule(run(curp=curp + curp_check_digit(curp)), "ine.curp_format")["status"] == "failed"

    def test_lowercase_and_spaces_are_tolerated(self):
        assert rule(run(curp=" pelj900515hdfrpn07 "), "ine.curp_format")["status"] == "passed"


class TestClaveElectorFormat:
    @pytest.mark.parametrize("clave", ["PRLPJN90051509X000", "PRLPJN9005150H000", "PRLPJ190051509H000"])
    def test_bad_structure_fails(self, clave):
        assert rule(run(clave_elector=clave), "ine.clave_elector_format")["status"] == "failed"


class TestNotExpired:
    @pytest.mark.parametrize("year, status", [("2031", "passed"), ("2026", "passed"), ("2025", "failed")])
    def test_valid_through_december_31_of_its_year(self, year, status):
        assert rule(run(fecha_vencimiento=year), "ine.not_expired")["status"] == status

    def test_last_year_fails_on_january_1(self):
        result = validate("ine", {**VALID_INE, "fecha_vencimiento": "2026"}, today=date(2027, 1, 1))

        assert rule(result, "ine.not_expired")["status"] == "failed"
        assert result["valid"] is False

    def test_value_that_is_not_a_year_fails(self):
        # Normalization reduces "2021-2031" to "2031"; anything still not a year is reported, not guessed.
        assert rule(run(fecha_vencimiento="VIGENTE"), "ine.not_expired")["status"] == "failed"


class TestMexicoCalendar:
    """Expiration is judged on Config.TZ's date, not the server's (UTC in containers)."""

    def test_new_year_in_utc_is_still_december_31_in_mexico(self, monkeypatch):
        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                # 2027-01-01 03:00 UTC = 2026-12-31 21:00 in Mexico City (UTC-6).
                return datetime(2027, 1, 1, 3, 0, tzinfo=timezone.utc).astimezone(tz)

        monkeypatch.setattr(validation_engine, "datetime", FrozenDatetime)

        assert local_today() == date(2026, 12, 31)
        result = validate("ine", {**VALID_INE, "fecha_vencimiento": "2026"})
        assert rule(result, "ine.not_expired")["status"] == "passed"


class TestCurpMatchesBirthDate:
    def test_different_birth_date_fails(self):
        assert rule(run(fecha_nacimiento="1990-05-16"), "ine.curp_matches_birth_date")["status"] == "failed"

    def test_born_in_2000s_uses_the_letter_homoclave(self):
        result = run(curp="PELJ050515HDFRPNA8", fecha_nacimiento="2005-05-15", clave_elector="PRLPJN05051509H000")

        assert rule(result, "ine.curp_matches_birth_date")["status"] == "passed"

    def test_same_digits_in_another_century_fail(self):
        # Digit homoclave = 1900s, so 1990 ≠ 2090 even though YYMMDD is identical.
        assert rule(run(fecha_nacimiento="2090-05-15"), "ine.curp_matches_birth_date")["status"] == "failed"

    def test_birth_date_not_normalized_fails_with_a_clear_message(self):
        entry = rule(run(fecha_nacimiento="15 de mayo"), "ine.curp_matches_birth_date")

        assert entry["status"] == "failed"
        assert "YYYY-MM-DD" in entry["message"]


class TestClaveMatchesCurp:
    def test_different_birth_date_fails(self):
        assert rule(run(clave_elector="PRLPJN90051609H000"), "ine.clave_matches_curp")["status"] == "failed"

    def test_different_sex_fails(self):
        assert rule(run(clave_elector="PRLPJN90051509M000"), "ine.clave_matches_curp")["status"] == "failed"

    def test_curp_with_sex_x_skips_the_sex_comparison(self):
        curp = "PELJ900515XDFRPN0"
        assert rule(run(curp=curp + curp_check_digit(curp)), "ine.clave_matches_curp")["status"] == "passed"


class TestNamesMatchCurp:
    """Initials vs CURP positions 1, 3, 4; a mismatch is a warning and never invalidates."""

    def test_mismatch_is_a_warning(self):
        result = run(apellido_paterno="GOMEZ")
        entry = rule(result, "ine.names_match_curp")

        assert (entry["status"], entry["severity"]) == ("failed", "warning")
        assert "apellidoPaterno" in entry["message"]
        assert result["valid"] is True
        assert result["summary"]["warnings"] == 1

    def test_compound_given_name_maria_uses_the_next_name(self):
        curp = "LOMM850101MDFPRR05"
        result = run(nombre="MARIA MERCEDES", apellido_paterno="LOPEZ", apellido_materno="MARTINEZ", curp=curp,
                     fecha_nacimiento="1985-01-01", clave_elector="LPMRMR85010109M000")

        assert rule(result, "ine.names_match_curp")["status"] == "passed"

    def test_missing_second_surname_is_x(self):
        curp = "PEXJ900515HDFRPN0"
        result = run(apellido_materno=None, curp=curp + curp_check_digit(curp))

        assert rule(result, "ine.names_match_curp")["status"] == "passed"
        assert rule(result, "ine.required_fields")["status"] == "passed"  # second surname is optional

    def test_surname_particles_accents_and_enye(self):
        curp = "XEAJ900515HDFRPN0"
        result = run(apellido_paterno="Ñúñez", apellido_materno="DE LA ÁLVAREZ", curp=curp + curp_check_digit(curp))

        assert rule(result, "ine.names_match_curp")["status"] == "passed"


class TestDocumentDetected:
    """Hybrid rule: the AI reports what it sees, the rule decides."""

    def test_other_document_fails(self):
        result = run(documento_detectado="comprobante_domicilio")

        assert rule(result, "ine.document_detected")["status"] == "failed"
        assert result["valid"] is False

    def test_case_and_spaces_are_tolerated(self):
        assert rule(run(documento_detectado=" INE "), "ine.document_detected")["status"] == "passed"

    def test_missing_observation_is_skipped(self):
        assert rule(run(documento_detectado=None), "ine.document_detected")["status"] == "skipped"


class TestMissingData:
    def test_missing_curp_is_reported_once_and_dependent_rules_are_skipped(self):
        result = run(curp=None)

        required = rule(result, "ine.required_fields")
        assert (required["status"], required["fields"]) == ("failed", ["curp"])
        for code in ("ine.curp_format", "ine.curp_matches_birth_date", "ine.clave_matches_curp", "ine.names_match_curp"):
            assert rule(result, code)["status"] == "skipped"
        assert result["summary"] == {"passed": 3, "failed": 1, "warnings": 0, "skipped": 4}
        assert result["valid"] is False

    def test_blank_strings_count_as_missing(self):
        assert rule(run(nombre="  "), "ine.required_fields")["fields"] == ["nombre"]


class TestPrivacyAndRegistry:
    def test_messages_never_include_document_values(self):
        result = run(curp="PELJ900515HDFRPN08", fecha_nacimiento="1991-01-01", apellido_paterno="GOMEZ")
        messages = " ".join(entry["message"] for entry in result["rules"])

        for value in ("PELJ900515HDFRPN08", "1991-01-01", "GOMEZ", "JUAN", "PRLPJN90051509H000"):
            assert value not in messages

    def test_rule_codes_are_unique_and_namespaced(self):
        codes = [r.code for r in RULES_BY_DOCUMENT_TYPE["ine"]]

        assert len(codes) == len(set(codes))
        assert all(code.startswith("ine.") for code in codes)

    def test_types_without_rules_return_none(self):
        assert validate("csf", {"rfc": "XAXX010101AAA"}, today=TODAY) is None


class TestVerdict:
    """One global answer: valid, invalid, incomplete or not_validated."""

    def verdict(self, **changes) -> dict:
        from app.rules.validation_engine import build_verdict

        return build_verdict("ine", run(**changes), "unused")

    def test_valid(self):
        verdict = self.verdict()

        assert verdict["status"] == "valid"
        assert verdict["failedRules"] == [] and verdict["warnings"] == []
        assert verdict["message"] == "The ine document is valid: every rule passed."

    def test_valid_with_warnings_lists_them(self):
        verdict = self.verdict(apellido_paterno="GOMEZ")

        assert verdict["status"] == "valid"
        assert verdict["warnings"] == ["ine.names_match_curp"]
        assert "1 warning(s)" in verdict["message"]

    def test_a_content_rule_failing_is_invalid(self):
        verdict = self.verdict(fecha_vencimiento="2020")

        assert verdict["status"] == "invalid"
        assert verdict["failedRules"] == ["ine.not_expired"]

    def test_only_missing_data_is_incomplete(self):
        verdict = self.verdict(curp=None)

        assert verdict["status"] == "incomplete"
        assert verdict["failedRules"] == ["ine.required_fields"]

    def test_wrong_document_is_invalid_even_with_missing_data(self):
        verdict = self.verdict(curp=None, documento_detectado="comprobante_domicilio")

        assert verdict["status"] == "invalid"
        assert set(verdict["failedRules"]) == {"ine.required_fields", "ine.document_detected"}

    def test_not_validated_carries_the_reason(self):
        from app.rules.validation_engine import build_verdict

        verdict = build_verdict("csf", None, "Not validated: no business rules for csf yet.")

        assert verdict == {"status": "not_validated", "documentType": "csf",
                           "message": "Not validated: no business rules for csf yet.", "failedRules": [], "warnings": []}
