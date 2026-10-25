import pytest

from app.utils.date_normalizer import normalize_date, normalize_dates


class TestNormalizeDate:
    """Dates as printed on Mexican bills become ISO; anything ambiguous is left alone."""

    @pytest.mark.parametrize("printed, expected", [
        ("2026-10-14", "2026-10-14"),
        ("14 OCT 26", "2026-10-14"),
        ("14-OCT-2026", "2026-10-14"),
        ("14 oct. 2026", "2026-10-14"),
        ("14 de octubre de 2026", "2026-10-14"),
        ("01 SEPT 26", "2026-09-01"),
        ("05/10/2026", "2026-10-05"),
        ("05.10.26", "2026-10-05"),
        ("  14   OCT   26 ", "2026-10-14"),
    ])
    def test_printed_formats_become_iso(self, printed, expected):
        assert normalize_date(printed) == expected

    def test_numeric_dates_are_day_first(self):
        # Mexico prints DD/MM/YYYY: 03/04 is April 3rd, never March 4th.
        assert normalize_date("03/04/2026") == "2026-04-03"

    @pytest.mark.parametrize("value", ["31/02/2026", "14 XYZ 26", "octubre 2026", "2026-13-01", ""])
    def test_unreadable_or_impossible_dates_are_left_alone(self, value):
        assert normalize_date(value) == value

    def test_non_string_passes_through(self):
        assert normalize_date(None) is None


class TestNormalizeDates:
    """Only the known date fields are touched."""

    def test_known_keys_are_normalized_and_others_pass_through(self):
        fields = {"fecha_emision": "14 OCT 26", "numero_servicio": "05/10/2026", "periodo_fin": None}

        assert normalize_dates(fields) == {
            "fecha_emision": "2026-10-14",
            "numero_servicio": "05/10/2026",
            "periodo_fin": None,
        }
