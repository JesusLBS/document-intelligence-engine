import base64

from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GeminiExtractor(BaseAiExtractor):
    """AI extractor using Google Gemini API (multimodal support)."""

    provider_name = "gemini"
    # Gemini reads PDFs natively (text layer + page images), so it gets the document itself.
    accepts_document_file = True

    # Thinking tokens count against this limit on Gemini 3, so it must leave room for them.
    MAX_OUTPUT_TOKENS = 8192

    def extract(
        self,
        text: str,
        requested_fields: list[str],
        document_type: str = None,
        diagnosis: dict = None,
        all_fields: bool = False,
        document_file: str = None,
        document_mime_type: str = None,
        name_hints: dict = None,
    ) -> dict:
        """
        Extract fields from the document file (and its text as reference) using Gemini.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.
            all_fields (bool): If True, extract all available fields.
            document_file (str, optional): File with only the requested pages, sent inline (base64).
            document_mime_type (str, optional): Its media type ('application/pdf', 'image/png'...).
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            dict: Extracted fields in snake_case.

        Raises:
            AiProviderNotConfiguredException: If GEMINI_API_KEY is empty.
            AiProviderException: If the call fails or the answer is blocked, truncated or not JSON.
        """
        if not text.strip() and not document_file:
            Logger.warning("GeminiExtractor received no text and no document", document_type=document_type)
            return {}

        self._require_api_key(Config.GEMINI_API_KEY, "GEMINI_API_KEY")

        prompt = self._build_prompt(text, requested_fields, document_type, diagnosis, all_fields, name_hints=name_hints)

        Logger.info(
            "Sending request to Gemini API",
            document_type=document_type,
            model=Config.GEMINI_MODEL,
            with_document=bool(document_file),
            document_mime_type=document_mime_type,
            text_chars=len(text.strip()),
        )

        url = f"{Config.GEMINI_API_URL}/{Config.GEMINI_MODEL}:generateContent"

        headers = {
            "x-goog-api-key": Config.GEMINI_API_KEY,
            "Content-Type": "application/json",
        }

        parts = [{"text": prompt}]

        if document_file:
            parts.append(self._build_file_part(document_file, document_mime_type))

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

    def _build_file_part(self, file_path: str, mime_type: str) -> dict:
        """
        Build a Gemini inline_data part from a document file (PDF up to 50 MB, or an image).

        Args:
            file_path (str): Path to the file.
            mime_type (str): Its media type.

        Returns:
            dict: Gemini-compatible inline_data part.
        """
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return {
            "inline_data": {
                "mime_type": mime_type,
                "data": encoded,
            }
        }
