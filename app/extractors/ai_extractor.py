from app.config import Config
from app.extractors.base_extractor import BaseExtractor
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

        providers = {
            "gemini": GeminiExtractor,
            "groq": GroqExtractor,
        }

        provider_class = providers.get(provider.lower())

        if not provider_class:
            raise ValueError(f"AI provider '{provider}' is not registered.")

        Logger.info("AI provider resolved", provider=provider)
        return provider_class()

    def extract(
        self,
        text: str,
        requested_fields: list[str],
        document_type: str = None,
        diagnosis: dict = None,
        all_fields: bool = False,
        image_paths: list[str] = None,
    ) -> dict:
        """
        Delegate extraction to the resolved AI provider.

        Args:
            text (str): Raw text from document.
            requested_fields (list[str]): Fields to extract.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): OCR diagnosis metadata.
            all_fields (bool): If True, extract all available fields.
            image_paths (list[str], optional): Paths to page images for multimodal providers.

        Returns:
            dict: Extracted fields in snake_case.
        """
        name_hints = get_name_hints_from_text(text)

        if name_hints:
            Logger.info(
                "CURP name hints decoded",
                apellido_paterno=name_hints["apellido_paterno_initial"],
                apellido_materno=name_hints["apellido_materno_initial"],
                nombre=name_hints["nombre_initial"],
            )

        return self._client.extract(
            text,
            requested_fields,
            document_type=document_type,
            diagnosis=diagnosis,
            all_fields=all_fields,
            image_paths=image_paths,
            name_hints=name_hints,
        )