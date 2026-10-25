from abc import ABC, abstractmethod

from app.extractors.extraction_context import ExtractionContext


class BaseExtractor(ABC):
    """Base class for all document extractors."""

    # True when the extractor reads the document file itself (not only its text); the service
    # then exports the requested pages and passes them in ExtractionContext.document_file.
    accepts_document_file: bool = False

    @abstractmethod
    def extract(self, text: str, requested_fields: list[str], context: ExtractionContext | None = None) -> dict:
        """
        Extract fields from raw text.

        Args:
            text (str): Raw text from document processor.
            requested_fields (list[str]): Fields requested by client. Empty means all.
            context (ExtractionContext, optional): Request details (document type, diagnosis,
                document file). Extractors that don't need it ignore it.

        Returns:
            dict: Extracted fields in snake_case.
        """
        pass

    def _filter_fields(self, data: dict, requested_fields: list[str]) -> dict:
        """
        Filter extracted data to only requested fields.

        Args:
            data (dict): All extracted fields.
            requested_fields (list[str]): Fields to keep. Empty returns all.

        Returns:
            dict: Filtered fields.
        """
        if not requested_fields:
            return data
        return {k: v for k, v in data.items() if k in requested_fields}
