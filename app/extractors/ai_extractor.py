from app.config import Config
from app.extractors.base_extractor import BaseExtractor
from app.extractors.extraction_context import ExtractionContext
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger
from app.utils.curp_decoder import get_name_hints_from_text


class AiExtractor(BaseExtractor):
    """
    Orchestrator that delegates extraction to the configured AI provider.
    Provider is resolved from Config.AI_PROVIDER or overridden per request.
    """

    def __init__(self, provider: str = None):
        """
        Initialize with optional provider override.

        Args:
            provider (str, optional): Override AI provider ('gemini', 'groq', 'claude').
                                      Defaults to Config.AI_PROVIDER.
        """
        self._provider = provider or Config.AI_PROVIDER
        self._client = self._resolve_provider(self._provider)

    @property
    def provider(self) -> str:
        """
        Name of the resolved AI provider.

        Returns:
            str: Provider name (e.g. 'gemini').
        """
        return self._provider

    @property
    def accepts_document_file(self) -> bool:
        """
        Whether the resolved provider reads the document file (Gemini) or only text (Groq).

        Returns:
            bool: The provider's capability.
        """
        return self._client.accepts_document_file

    def _resolve_provider(self, provider: str) -> BaseAiExtractor:
        """
        Resolve AI provider instance.

        Args:
            provider (str): Provider name.

        Returns:
            BaseAiExtractor: Concrete provider instance.

        Raises:
            ValueError: If provider is not registered.
        """
        from app.extractors.ai.gemini_extractor import GeminiExtractor
        from app.extractors.ai.groq_extractor import GroqExtractor

        # Keep keys in sync with Config.AI_PROVIDERS (used by request validation).
        providers = {
            "gemini": GeminiExtractor,
            "groq": GroqExtractor,
        }

        provider_class = providers.get(provider.lower())

        if not provider_class:
            raise ValueError(f"AI provider '{provider}' is not registered.")

        Logger.info("AI provider resolved", provider=provider)
        return provider_class()

    def extract(self, text: str, requested_fields: list[str], context: ExtractionContext | None = None) -> dict:
        """
        Delegate extraction to the resolved AI provider.

        Args:
            text (str): Raw text from document.
            requested_fields (list[str]): Fields to extract.
            context (ExtractionContext, optional): Document type, OCR diagnosis, all_fields flag
                and, for providers that read documents, the file with the requested pages.

        Returns:
            dict: Extracted fields in snake_case.
        """
        context = context or ExtractionContext()
        name_hints = get_name_hints_from_text(text)

        if name_hints:
            # Never log the decoded initials: they are derived from personal data.
            Logger.info("CURP name hints decoded", provider=self._provider)

        return self._client.extract(
            text,
            requested_fields,
            document_type=context.document_type,
            diagnosis=context.diagnosis,
            all_fields=context.all_fields,
            document_file=context.document_file,
            document_mime_type=context.document_mime_type,
            name_hints=name_hints,
        )