import re

from app.extractors.base_extractor import BaseExtractor


class ComprobanteDomicilioExtractor(BaseExtractor):
    """
    Extractor for comprobante de domicilio documents (Telmex, CFE, Izzi, etc.).

    NOTE: Regex-based extraction is not suitable for this document type due to
    variable structure across providers. This extractor is a placeholder until
    AiExtractor is implemented as the default strategy for this document type.
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
            "rfc": None,
            "direccion": None,
            "colonia": None,
            "municipio": None,
            "estado": None,
            "codigo_postal": None,
            "periodo": None,
            "fecha_emision": None,
            "numero_cuenta": None,
            "empresa": None,
        }
        return self._filter_fields(data, requested_fields)