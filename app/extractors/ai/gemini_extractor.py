import json
import requests

from app.config import Config
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GeminiExtractor(BaseAiExtractor):
    """AI extractor using Google Gemini API (multimodal support)."""

    def extract(self, text: str, requested_fields: list[str], document_type: str = None, diagnosis: dict = None, all_fields: bool = False) -> dict:
        """
        Extract fields from text using Gemini LLM.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.
            all_fields (bool): If True, extract all available fields.

        Returns:
            dict: Extracted fields in snake_case.
        """
        if not text or not text.strip():
            Logger.warning("GeminiExtractor received empty text", document_type=document_type)
            return {}

        prompt = self._build_prompt(text, requested_fields, document_type, diagnosis, all_fields)

        Logger.info("Sending request to Gemini API", document_type=document_type, model=Config.GEMINI_MODEL)

        url = f"{Config.GEMINI_API_URL}/{Config.GEMINI_MODEL}:generateContent"

        headers = {
            "x-goog-api-key": Config.GEMINI_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            Logger.error("Gemini API error", status=response.status_code, detail=response.text)
            raise RuntimeError(f"Gemini API returned {response.status_code}: {response.text}")

        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_response(raw)