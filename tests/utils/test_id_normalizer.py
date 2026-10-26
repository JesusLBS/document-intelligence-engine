import pytest

from app.utils.id_normalizer import (
    curp_check_digit, normalize_clave_elector, normalize_curp, normalize_identifiers, recover_identifiers,
    resolve_curp_century,
)


VALID_CURP = "XAXX010101HDFAAA09"
VALID_CLAVE = "XAXXXX01010109H000"


class TestNormalizeCurp:
    """Look-alike OCR errors are fixed by position, only when the result is a valid CURP."""

    def test_valid_curp_is_unchanged(self):
        assert normalize_curp(VALID_CURP) == VALID_CURP

    def test_letter_o_in_digit_positions_becomes_zero(self):
        # Real case on the INE sample: OCR read a 0 of the birth date as the letter O.
        assert normalize_curp("XAXXO1O1O1HDFAAA09") == VALID_CURP

    def test_digit_in_letter_positions_becomes_letter(self):
        assert normalize_curp("XAX0010101HDFAAA09") == "XAXO010101HDFAAA09"

    def test_spaces_and_case_are_normalized(self):
        assert normalize_curp("xaxx 010101 hdfaaa09") == VALID_CURP

    def test_wrong_length_is_left_alone(self):
        assert normalize_curp("XAXX010101HDFAAA0") == "XAXX010101HDFAAA0"

    def test_unfixable_value_is_left_alone(self):
        # Position 11 must be H/M/X; nothing to swap there, so no guess is made.
        assert normalize_curp("XAXX010101QDFAAA09") == "XAXX010101QDFAAA09"

    def test_non_string_passes_through(self):
        assert normalize_curp(None) is None


class TestNormalizeClaveElector:
    """Same positional correction for the INE clave de elector."""

    def test_valid_clave_is_unchanged(self):
        assert normalize_clave_elector(VALID_CLAVE) == VALID_CLAVE

    def test_look_alikes_are_fixed(self):
        assert normalize_clave_elector("XAXXXXO1O1O1O9HOOO") == VALID_CLAVE


class TestNormalizeIdentifiers:
    """Only known identifier keys are touched."""

    def test_known_keys_are_normalized_and_others_pass_through(self):
        fields = {"curp": "XAXXO1O1O1HDFAAA09", "nombre": "JUAN O", "clave_elector": None}

        assert normalize_identifiers(fields) == {"curp": VALID_CURP, "nombre": "JUAN O", "clave_elector": None}


class TestRecoverIdentifiers:
    """An identifier the AI left empty is taken from the text only when exactly one valid candidate exists."""

    CURP = "PELJ900515HDFRPN07"  # fictitious, valid check digit
    CLAVE = "PRLPJN90051509H000"

    def test_empty_curp_is_recovered_from_ocr_text_with_a_look_alike(self):
        text = "CLAVE DE ELECTOR PRLPJN90051509H000\nCURP PELJ9OO515HDFRPN07\n"  # O instead of 0, as OCR reads it

        assert recover_identifiers({"curp": None, "nombre": "JUAN"}, text) == {"curp": self.CURP, "nombre": "JUAN"}

    def test_empty_clave_is_recovered(self):
        assert recover_identifiers({"clave_elector": ""}, f"CLAVE {self.CLAVE}")["clave_elector"] == self.CLAVE

    def test_values_returned_by_the_ai_are_never_replaced(self):
        fields = {"curp": "XAXX010101HDFAAA09"}

        assert recover_identifiers(fields, f"CURP {self.CURP}") == fields

    def test_wrong_check_digit_is_not_recovered(self):
        assert recover_identifiers({"curp": None}, "CURP PELJ900515HDFRPN08")["curp"] is None

    def test_two_valid_candidates_are_ambiguous(self):
        other = "PELJ050515HDFRPNA8"  # also valid
        assert recover_identifiers({"curp": None}, f"{self.CURP} {other}")["curp"] is None

    def test_fields_not_requested_are_not_added(self):
        assert recover_identifiers({"nombre": "JUAN"}, f"CURP {self.CURP}") == {"nombre": "JUAN"}


class TestResolveCurpCentury:
    """Position 17 (digit before 2000, letter from 2000) vs the birth date; O/0 is invisible to the check digit."""

    def test_o_read_instead_of_zero_is_fixed_for_people_born_before_2000(self):
        # Fictitious case reproducing a real INE (2026-10-25): OCR read the homoclave 0 as O.
        fields = {"curp": "PELJ900515HDFRPNO7", "fecha_nacimiento": "1990-05-15"}

        assert resolve_curp_century(fields)["curp"] == "PELJ900515HDFRPN07"

    def test_o_and_zero_share_the_check_digit(self):
        assert curp_check_digit("PELJ900515HDFRPNO") == curp_check_digit("PELJ900515HDFRPN0")

    def test_zero_read_instead_of_o_is_fixed_for_people_born_from_2000(self):
        fields = {"curp": "PELJ050515HDFRPN08", "fecha_nacimiento": "2005-05-15"}

        assert resolve_curp_century(fields)["curp"] == "PELJ050515HDFRPNO8"

    @pytest.mark.parametrize("fields", [
        {"curp": "PELJ900515HDFRPN07", "fecha_nacimiento": "1990-05-15"},   # already consistent
        {"curp": "PELJ900515HDFRPNA7", "fecha_nacimiento": "1990-05-15"},   # a letter that is not a look-alike of 0
        {"curp": "PELJ900515HDFRPNO7", "fecha_nacimiento": "15/05/1990"},   # birth date not normalized
        {"curp": "PELJ900515HDFRPNO7"},                                      # no birth date
        {"curp": None, "fecha_nacimiento": "1990-05-15"},
    ])
    def test_nothing_changes_without_unambiguous_evidence(self, fields):
        assert resolve_curp_century(fields) == fields
