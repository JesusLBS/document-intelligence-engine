from app.extractors.base_extractor import BaseExtractor
from app.extractors.csf_extractor import CsfExtractor
from app.exceptions.extractor_not_found_exception import ExtractorNotFoundException



EXTRACTOR_MAP = {
    "csf": CsfExtractor,
}


class ExtractorFactory:
    """Resolves the correct extractor based on document type."""

    @staticmethod
    def make(document_type: str) -> BaseExtractor:
        """
        Return extractor instance for the given document type.

        Args:
            document_type (str): Document type (e.g. 'csf', 'ine').

        Returns:
            BaseExtractor: Concrete extractor instance.

        Raises:
            ValueError: If no extractor is registered for the document type.
        """
        extractor_class = EXTRACTOR_MAP.get(document_type.lower())

        if not extractor_class:
            raise ExtractorNotFoundException(document_type)

        return extractor_class()