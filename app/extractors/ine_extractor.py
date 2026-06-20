import re

from app.extractors.base_extractor import BaseExtractor


class IneExtractor(BaseExtractor):
    """
    Extractor for INE (Credencial para Votar) documents.

    NOTE: Regex-based extraction is not suitable for this document type due to
    variable scan quality and multiple INE generations with different layouts.
    This extractor is a placeholder until AiExtractor is implemented.
    """

    def extract(self, text: str, requested_fields: list[str]) -> dict:
        """
        Extract comprobante de domicilio fields from raw text.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.

        Returns:
            dict: Extracted fields in snake_case. All null until AiExtractor is implemented.
        """
        data = {
            "nombre": None,
            "apellido_paterno": None,
            "apellido_materno": None,
            "curp": None,
            "fecha_nacimiento": None,
            "fecha_vencimiento": None,
            "clave_elector": None,
            "seccion": None,
            "direccion": None,
            "colonia": None,
            "municipio": None,
            "estado": None,
        }
        return self._filter_fields(data, requested_fields)