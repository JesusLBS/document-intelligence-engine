from app.utils.id_normalizer import normalize_clave_elector, normalize_curp, normalize_identifiers


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
