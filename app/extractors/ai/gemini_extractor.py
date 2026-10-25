import base64

from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GeminiExtractor(BaseAiExtractor):
    """AI extractor using Google Gemini API (multimodal support)."""

    provider_name = "gemini"

    # Thinking tokens count against this limit on Gemini 3, so it must leave room for them.
    MAX_OUTPUT_TOKENS = 8192

    def extract(
        self,
        text: str,
        requested_fields: list[str],
        document_type: str = None,
        diagnosis: dict = None,
        all_fields: bool = False,
        image_paths: list[str] = None,
        name_hints: dict = None,
    ) -> dict:
        """
        Extract fields from text and/or images using Gemini LLM.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.
            all_fields (bool): If True, extract all available fields.
            image_paths (list[str], optional): Paths to page images to send alongside text.
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            dict: Extracted fields in snake_case.

        Raises:
            AiProviderNotConfiguredException: If GEMINI_API_KEY is empty.
            AiProviderException: If the call fails or the answer is blocked, truncated or not JSON.
        """
        if not text.strip() and not image_paths:
            Logger.warning("GeminiExtractor received no text and no images", document_type=document_type)
            return {}

        self._require_api_key(Config.GEMINI_API_KEY, "GEMINI_API_KEY")

        prompt = self._build_prompt(text, requested_fields, document_type, diagnosis, all_fields, name_hints=name_hints)

        Logger.info(
            "Sending request to Gemini API",
            document_type=document_type,
            model=Config.GEMINI_MODEL,
            with_images=bool(image_paths),
            image_count=len(image_paths) if image_paths else 0,
        )

        url = f"{Config.GEMINI_API_URL}/{Config.GEMINI_MODEL}:generateContent"

        headers = {
            "x-goog-api-key": Config.GEMINI_API_KEY,
            "Content-Type": "application/json",
        }

        parts = [{"text": prompt}]

        if image_paths:
            for image_path in image_paths:
                parts.append(self._build_image_part(image_path))

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": self._generation_config(),
        }

        body = self._post_json(url, headers, payload, timeout=Config.GEMINI_TIMEOUT_SECONDS)
        return self._parse_response(self._answer_text(body))

    def _generation_config(self) -> dict:
        """
        Build generationConfig for the configured model.

        Temperature is left at the model default: Gemini 3 docs warn that lowering it
        can cause looping or degraded output.

        Returns:
            dict: Gemini generationConfig.
        """
        config = {
            "responseMimeType": "application/json",
            "maxOutputTokens": self.MAX_OUTPUT_TOKENS,
        }

        if Config.GEMINI_THINKING_LEVEL and self._supports_thinking_level(Config.GEMINI_MODEL):
            config["thinkingConfig"] = {"thinkingLevel": Config.GEMINI_THINKING_LEVEL}

        return config

    @staticmethod
    def _supports_thinking_level(model: str) -> bool:
        """
        Tell whether the model accepts thinkingConfig.thinkingLevel.

        Gemini 2.x rejects it with HTTP 400 ("Thinking level is not supported for this
        model", verified against gemini-2.5-flash); they keep their default thinking.

        Args:
            model (str): Gemini model id.

        Returns:
            bool: False for gemini-2.x models, True otherwise.
        """
        return not model.startswith("gemini-2")

    def _answer_text(self, body: dict) -> str:
        """
        Return the answer text from a generateContent response, skipping thought parts.

        Args:
            body (dict): Decoded generateContent response.

        Returns:
            str: Concatenated answer text.

        Raises:
            AiProviderException: If the prompt was blocked, there is no candidate,
                or the answer is empty (safety stop, MAX_TOKENS...).
        """
        block_reason = (body.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            raise AiProviderException(self.provider_name, f"blocked the request ({block_reason})")

        candidates = body.get("candidates") or []
        if not candidates:
            raise AiProviderException(self.provider_name, "returned no answer")

        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if not part.get("thought"))

        if not text.strip():
            finish_reason = candidate.get("finishReason", "unknown")
            raise AiProviderException(self.provider_name, f"returned an empty answer (finishReason={finish_reason})")

        return text

    def _build_image_part(self, image_path: str) -> dict:
        """
        Build a Gemini inline_data part from an image file.

        Args:
            image_path (str): Absolute path to the image file.

        Returns:
            dict: Gemini-compatible inline_data part.
        """
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {
            "inline_data": {
                "mime_type": "image/png",
                "data": encoded,
            }
        }
