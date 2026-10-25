from app.extractors.base_extractor import BaseExtractor
from app.extractors.extraction_context import ExtractionContext


class PassthroughExtractor(BaseExtractor):
    """
    No-op extractor for document types without a registered regex extractor.
    Returns empty extracted fields without raising errors.
    Used when client sends extractor=regex but no regex extractor exists for the document type.
    """

    def extract(self, text: str, requested_fields: list[str], context: ExtractionContext | None = None) -> dict:
        """
        Return empty dict — no extraction performed.

        Args:
            text (str): Raw text (ignored).
            requested_fields (list[str]): Requested fields (ignored).
            context (ExtractionContext, optional): Ignored.

        Returns:
            dict: Empty dict.
        """
        return {}