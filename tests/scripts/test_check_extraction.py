import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_extraction.py"
spec = importlib.util.spec_from_file_location("check_extraction", SCRIPT)
check_extraction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_extraction)


class TestMatches:
    """Field comparison used by make check-extraction."""

    def test_plain_values_ignore_case_and_spacing(self):
        assert check_extraction.matches("AV DE LOS EJEMPLOS", "av  de los ejemplos")
        assert not check_extraction.matches("AV DE LOS EJEMPLOS", "AVENIDA DE LOS EJEMPLOS")

    def test_list_accepts_any_option(self):
        assert check_extraction.matches(["CENTRO", "COL. CENTRO"], "col. centro")

    def test_hashed_reference_compares_fingerprints(self):
        expected = {"sha256": check_extraction.fingerprint("XAXX010101HDFAAA09")}

        assert check_extraction.matches(expected, "xaxx010101hdfaaa09")
        assert not check_extraction.matches(expected, "XAXX010101HDFAAA08")

    def test_null_reference_requires_an_empty_field(self):
        assert check_extraction.matches(None, None)
        assert not check_extraction.matches(None, "4")

    def test_hashed_fields_never_show_the_value(self):
        assert check_extraction.describe("curp", {"sha256": "x"}, "XAXX010101HDFAAA09") == "curp"
        assert check_extraction.describe("calle", "AV X", "AV Y") == "calle='AV Y'"
