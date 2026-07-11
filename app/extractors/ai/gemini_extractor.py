import base64

import requests

from app.config import Config
from app.extractors.ai.base_ai_extractor import BaseAiExtractor
from app.helpers.logger import Logger


class GeminiExtractor(BaseAiExtractor):
    """AI extractor using Google Gemini API (multimodal support)."""

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
        """
        if not text.strip() and not image_paths:
            Logger.warning("GeminiExtractor received no text and no images", document_type=document_type)
            return {}

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
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2000,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            Logger.error("Gemini API error", status=response.status_code, detail=response.text)
            raise RuntimeError(f"Gemini API returned {response.status_code}: {response.text}")

        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_response(raw)

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