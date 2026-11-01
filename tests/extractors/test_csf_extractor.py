import pytest

from app.extractors.csf_extractor import CsfExtractor


SAMPLE_CSF_TEXT = """Página  [1] de [2] 
CÉDULA DE IDENTIFICACIÓN FISCAL 
XAXX010101AAA
Registro Federal de Contribuyentes
JUAN PEREZ LOPEZ
Nombre, denominación o razón 
social
idCIF: 22090114178
VALIDA TU INFORMACIÓN 
FISCAL
CONSTANCIA DE SITUACIÓN FISCAL
Lugar y Fecha de Emisión
CIUDAD DE MEXICO , MEXICO A 15 DE MAYO DE 2025
XAXX010101AAA
Datos de Identificación del Contribuyente: 
RFC:
XAXX010101AAA
CURP:
XAXX010101HDFAAA09
Nombre (s):
JUAN
Primer Apellido:
PEREZ
Segundo Apellido:
LOPEZ
Fecha inicio de operaciones:
20 DE SEPTIEMBRE DE 2023
Estatus en el padrón:
ACTIVO
Fecha de último cambio de estado:
05 DE SEPTIEMBRE DE 2022
Nombre Comercial:
Datos del domicilio registrado 
Código Postal:52760
Página  [2] de [2] 
Actividades Económicas: 
Orden
Actividad Económica
Porcentaje
Fecha Inicio
Fecha Fin
1
Asalariado
100
20/09/2023
Regímenes:  
Régimen
Fecha Inicio
Fecha Fin
Régimen de Sueldos y Salarios e Ingresos Asimilados a Salarios
20/09/2023
Sus datos personales son incorporados y protegidos en los sistemas del SAT"""


class TestCsfExtractor:
    """Tests for CsfExtractor field extraction against sample CSF text structure."""

    @pytest.fixture
    def extractor(self) -> CsfExtractor:
        """Return a fresh CsfExtractor instance."""
        return CsfExtractor()

    def test_extracts_rfc(self, extractor):
        """RFC should be correctly extracted from text."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["rfc"] == "XAXX010101AAA"

    def test_extracts_curp(self, extractor):
        """CURP should be correctly extracted from text."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["curp"] == "XAXX010101HDFAAA09"

    def test_extracts_first_name(self, extractor):
        """First name should be correctly extracted."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["first_name"] == "JUAN"

    def test_extracts_last_name(self, extractor):
        """Last name should combine first and second surname."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["last_name"] == "PEREZ LOPEZ"

    def test_extracts_full_name(self, extractor):
        """Full name should combine first name and last name."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["full_name"] == "JUAN PEREZ LOPEZ"

    def test_extracts_padron_status(self, extractor):
        """Padron status should be correctly extracted."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["padron_status"] == "ACTIVO"

    def test_extracts_issued_place_and_date(self, extractor):
        """Issued place and date should be correctly extracted."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert result["issued_at"] == "15 DE MAYO DE 2025"
        assert "CIUDAD DE MEXICO" in result["issued_place"]

    def test_extracts_economic_activities(self, extractor):
        """Economic activities should return a non-empty list."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert isinstance(result["economic_activities"], list)
        assert len(result["economic_activities"]) > 0

    def test_extracts_tax_regimes(self, extractor):
        """Tax regimes should return a non-empty list."""
        result = extractor.extract(SAMPLE_CSF_TEXT, [])
        assert isinstance(result["tax_regimes"], list)
        assert len(result["tax_regimes"]) > 0

    def test_filters_requested_fields(self, extractor):
        """When requested_fields is provided, only those keys should be returned."""
        result = extractor.extract(SAMPLE_CSF_TEXT, ["rfc", "curp"])
        assert set(result.keys()) == {"rfc", "curp"}

    def test_returns_none_for_missing_fields(self, extractor):
        """Fields not found in text should return None, not raise."""
        result = extractor.extract("texto sin nada relevante", [])
        assert result["rfc"] is None
        assert result["curp"] is None

class TestCsfObservationAndDate:
    """Fields the CSF rules need, produced by the regex extractor too."""

    def test_heading_is_reported_as_csf(self):
        assert CsfExtractor().extract(SAMPLE_CSF_TEXT, ["documento_detectado"]) == {"documento_detectado": "csf"}

    def test_text_without_the_heading_is_reported_as_otro(self):
        assert CsfExtractor().extract("RECIBO DE LUZ", ["documento_detectado"]) == {"documento_detectado": "otro"}

    def test_issue_date_is_returned_as_printed_for_the_normalizer(self):
        from app.utils.date_normalizer import normalize_dates

        printed = CsfExtractor().extract(SAMPLE_CSF_TEXT, ["issued_at"])

        assert printed == {"issued_at": "15 DE MAYO DE 2025"}
        assert normalize_dates(printed) == {"issued_at": "2025-05-15"}

    def test_persona_moral_company_name_is_extracted(self):
        text = "CONSTANCIA DE SITUACIÓN FISCAL\nRFC:\nABC200101XY3\nDenominación/Razón Social:\nEMPRESA EJEMPLO S.A. DE C.V.\n"

        assert CsfExtractor().extract(text, ["full_name", "curp"]) == {
            "full_name": "EMPRESA EJEMPLO S.A. DE C.V.",
            "curp": None,
        }
