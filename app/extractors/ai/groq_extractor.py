from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GroqExtractor(BaseAiExtractor):
    """AI extractor using Groq API (text-only, no multimodal support)."""

    provider_name = "groq"

    # Reasoning models (gpt-oss) spend part of the completion budget reasoning.
    MAX_COMPLETION_TOKENS = 4096

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
        Extract fields from text using Groq LLM. Images are ignored — Groq is text-only.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.
            all_fields (bool): If True, extract all available fields.
            document_file (str, optional): Ignored — Groq reads text only (accepts_document_file is False).
            document_mime_type (str, optional): Ignored.
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            dict: Extracted fields in snake_case.

        Raises:
            AiProviderNotConfiguredException: If GROQ_API_KEY is empty.
            AiProviderException: If the call fails or the answer is empty or not JSON.
        """
        if not text or not text.strip():
            Logger.warning("GroqExtractor received empty text", document_type=document_type)
            return {}

        self._require_api_key(Config.GROQ_API_KEY, "GROQ_API_KEY")

        prompt = self._build_prompt(
            text, requested_fields, document_type, diagnosis, all_fields, name_hints=name_hints
        )

        Logger.info("Sending request to Groq API", document_type=document_type, model=Config.GROQ_MODEL)

        headers = {
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        body = self._post_json(Config.GROQ_API_URL, headers, self._payload(prompt), timeout=Config.GROQ_TIMEOUT_SECONDS)
        return self._parse_response(self._answer_text(body))

    def _payload(self, prompt: str) -> dict:
        """
        Build the chat completions payload in JSON mode.

        Reasoning parameters are only sent when GROQ_REASONING_EFFORT is set, so the
        same code works with non-reasoning models.

        Args:
            prompt (str): Extraction prompt (already asks for a JSON object, required by JSON mode).

        Returns:
            dict: Groq chat completions payload.
        """
        payload = {
            "model": Config.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": self.MAX_COMPLETION_TOKENS,
        }

        if Config.GROQ_REASONING_EFFORT:
            payload["reasoning_effort"] = Config.GROQ_REASONING_EFFORT
            payload["include_reasoning"] = False

        return payload

    def _answer_text(self, body: dict) -> str:
        """
        Return the answer text from a chat completions response.

        Args:
            body (dict): Decoded chat completions response.

        Returns:
            str: Answer content.

        Raises:
            AiProviderException: If there is no choice or the content is empty.
        """
        choices = body.get("choices") or []
        if not choices:
            raise AiProviderException(self.provider_name, "returned no answer")

        content = (choices[0].get("message") or {}).get("content") or ""
        if not content.strip():
            finish_reason = choices[0].get("finish_reason", "unknown")
            raise AiProviderException(self.provider_name, f"returned an empty answer (finish_reason={finish_reason})")

        return content
