import re

from app.extractors.base_extractor import BaseExtractor


class CsfExtractor(BaseExtractor):
    """Extractor for Constancia de Situación Fiscal (CSF) documents."""

    def extract(self, text: str, requested_fields: list[str]) -> dict:
        """
        Extract CSF fields from raw text.

        Args:
            text (str): Raw text extracted from PDF.
            requested_fields (list[str]): Fields requested by client.

        Returns:
            dict: Extracted CSF fields in snake_case.
        """
        data = {
            "rfc": self._extract_rfc(text),
            "curp": self._extract_curp(text),
            "full_name": self._extract_full_name(text),
            "first_name": self._extract_first_name(text),
            "last_name": self._extract_last_name(text),
            "issued_at": self._extract_issued_at(text),
            "issued_place": self._extract_issued_place(text),
            "padron_status": self._extract_padron_status(text),
            "tax_regimes": self._extract_tax_regimes(text),
            "economic_activities": self._extract_economic_activities(text),
        }
        return self._filter_fields(data, requested_fields)

    def _extract_rfc(self, text: str) -> str | None:
        match = re.search(r'\b([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})\b', text)
        return match.group(1) if match else None

    def _extract_curp(self, text: str) -> str | None:
        match = re.search(r'\b([A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d)\b', text)
        return match.group(1) if match else None

    def _extract_full_name(self, text: str) -> str | None:
        # Matches: "Full Name" after "social\n"
        first = self._extract_first_name(text)
        last = self._extract_last_name(text)
        if first and last:
            return f"{first} {last}".strip()
        match = re.search(r'raz[oó]n\s*social\s*\n([A-ZÁÉÍÓÚÑ ]+)\n', text)
        return match.group(1).strip() if match else None

    def _extract_first_name(self, text: str) -> str | None:
        match = re.search(r'Nombre\s*\(s\)\s*:\s*\n([A-ZÁÉÍÓÚÑ ]+)\n', text)
        return match.group(1).strip() if match else None

    def _extract_last_name(self, text: str) -> str | None:
        first = re.search(r'Primer Apellido:\s*\n([A-ZÁÉÍÓÚÑ ]+)\n', text)
        second = re.search(r'Segundo Apellido:\s*\n([A-ZÁÉÍÓÚÑ ]+)\n', text)
        parts = []
        if first:
            parts.append(first.group(1).strip())
        if second:
            parts.append(second.group(1).strip())
        return " ".join(parts) if parts else None

    def _extract_issued_at(self, text: str) -> str | None:
        # Matches: "Municipio , MEXICO A 15 DE MAYO DE 2025"
        match = re.search(r'A\s+(\d{1,2}\s+DE\s+\w+\s+DE\s+\d{4})', text)
        return match.group(1).strip() if match else None

    def _extract_issued_place(self, text: str) -> str | None:
        # Matches place before "A DD DE MES DE YYYY"
        match = re.search(r'Lugar y Fecha de Emisi[oó]n\s*\n([A-ZÁÉÍÓÚÑ ,]+)\s+A\s+\d', text)
        return match.group(1).strip() if match else None

    def _extract_padron_status(self, text: str) -> str | None:
        match = re.search(r'Estatus en el padr[oó]n:\s*\n([A-ZÁÉÍÓÚÑ ]+)\n', text)
        return match.group(1).strip() if match else None

    def _extract_tax_regimes(self, text: str) -> list[str]:
        # Matches regime name before date pattern
        matches = re.findall(r'([\w\s\u00C0-\u024F]+)\n\d{2}/\d{2}/\d{4}(?:\n\d{2}/\d{2}/\d{4})?(?:\n|$)', text)
        regimes_section = re.search(r'Reg[íi]menes:(.*?)(?:Sus datos|$)', text, re.DOTALL)
        if not regimes_section:
            return []
        regime_matches = re.findall(r'^([A-ZÁÉÍÓÚÑ\w ]{10,})\n', regimes_section.group(1), re.MULTILINE)
        return [m.strip() for m in regime_matches if m.strip()]

    def _extract_economic_activities(self, text: str) -> list[str]:
        activities_section = re.search(r'Actividades Econ[oó]micas:(.*?)Reg[íi]menes:', text, re.DOTALL)
        if not activities_section:
            return []
        matches = re.findall(r'\d+\s+([A-ZÁÉÍÓÚÑ\w ]+)\s+\d+\s+\d{2}/\d{2}/\d{4}', activities_section.group(1))
        return [m.strip() for m in matches if m.strip()]