from app.extractors.base_extractor import BaseExtractor
from app.extractors.csf_extractor import CsfExtractor
from app.extractors.ai_extractor import AiExtractor
from app.extractors.passthrough_extractor import PassthroughExtractor
from app.exceptions.extractor_not_found_exception import ExtractorNotFoundException


EXTRACTOR_MAP = {
    "csf": CsfExtractor,
}


class ExtractorFactory:
    """Resolves the correct extractor based on document type and strategy."""

    @staticmethod
    def make(document_type: str, extractor_strategy: str = "regex", ai_provider: str = None) -> BaseExtractor:
        """
        Return extractor instance for the given document type and strategy.

        Args:
            document_type (str): Document type (e.g. 'csf', 'ine').
            extractor_strategy (str): Strategy from request ('regex' or 'ai').
            ai_provider (str, optional): AI provider override ('gemini', 'groq').

        Returns:
            BaseExtractor: Concrete extractor instance.
        """
        if extractor_strategy == "ai":
            return AiExtractor(provider=ai_provider)

        extractor_class = EXTRACTOR_MAP.get(document_type.lower())

        if extractor_class:
            return extractor_class()

        return PassthroughExtractor()