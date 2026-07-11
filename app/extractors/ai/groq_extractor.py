import requests

from app.config import Config
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GroqExtractor(BaseAiExtractor):
    """AI extractor using Groq API (text-only, no multimodal support)."""

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
        Extract fields from text using Groq LLM. Images are ignored — Groq is text-only.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.
            all_fields (bool): If True, extract all available fields.
            image_paths (list[str], optional): Ignored — Groq does not support images.
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            dict: Extracted fields in snake_case.
        """
        if image_paths:
            Logger.warning("GroqExtractor does not support images, ignoring image_paths", document_type=document_type)

        if not text or not text.strip():
            Logger.warning("GroqExtractor received empty text", document_type=document_type)
            return {}

        prompt = self._build_prompt(
            text, requested_fields, document_type, diagnosis, all_fields, name_hints=name_hints
        )

        Logger.info("Sending request to Groq API", document_type=document_type, model=Config.GROQ_MODEL)

        headers = {
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": Config.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        response = requests.post(Config.GROQ_API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            Logger.error("Groq API error", status=response.status_code, detail=response.text)
            raise RuntimeError(f"Groq API returned {response.status_code}: {response.text}")

        raw = response.json()["choices"][0]["message"]["content"]
        return self._parse_response(raw)