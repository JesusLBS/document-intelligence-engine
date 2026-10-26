from app.config import Config
from app.extractors.ai.groq_extractor import GroqExtractor


def build_prompt(document_type: str, requested_fields: list[str], all_fields: bool = False) -> str:
    return GroqExtractor()._build_prompt("OCR text", requested_fields, document_type, {}, all_fields)


class TestFieldDefinitions:
    """The shared prompt tells every provider what each known field means and its format."""

    def test_requested_fields_are_described(self):
        prompt = build_prompt("comprobante_domicilio", ["fecha_emision", "codigo_postal"])

        assert "Field definitions" in prompt
        assert "- fecha_emision: issue date of the bill, exactly as printed" in prompt
        assert "- codigo_postal:" in prompt
        assert "- calle:" not in prompt

    def test_all_fields_describes_every_known_field(self):
        prompt = build_prompt("comprobante_domicilio", [], all_fields=True)

        for name in Config.DOCUMENT_FIELD_DESCRIPTIONS["comprobante_domicilio"]:
            assert f"- {name}:" in prompt

    def test_types_without_descriptions_get_no_section(self):
        assert "Field definitions" not in build_prompt("csf", ["rfc"])

    def test_default_fields_are_all_described(self):
        # Every default field of the comprobante must tell the AI its meaning and format.
        descriptions = Config.DOCUMENT_FIELD_DESCRIPTIONS["comprobante_domicilio"]

        assert set(Config.DOCUMENT_DEFAULT_FIELDS["comprobante_domicilio"]) == set(descriptions)


class TestIneFieldDefinitions:
    def test_every_ine_default_field_is_described(self):
        descriptions = Config.DOCUMENT_FIELD_DESCRIPTIONS["ine"]

        assert set(Config.DOCUMENT_DEFAULT_FIELDS["ine"]) == set(descriptions)

    def test_dates_are_requested_as_printed_and_the_observation_is_explained(self):
        prompt = build_prompt("ine", Config.DOCUMENT_DEFAULT_FIELDS["ine"])

        assert "- fecha_vencimiento: VIGENCIA exactly as printed" in prompt
        assert "- documento_detectado: which document the file actually is" in prompt
