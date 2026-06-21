import json

import requests

from app.config import Config
from app.extractors.base_extractor import BaseExtractor
from app.helpers.logger import Logger
from app.config import Config

IA_API_URL = Config.GROQ_API_URL


class AiExtractor(BaseExtractor):
    """Extractor that uses Groq LLM API to extract fields from unstructured text."""

    def extract(self, text: str, requested_fields: list[str], document_type: str = None, diagnosis: dict = None, all_fields: bool = False) -> dict:
        """
        Extract fields from text using Groq LLM.

        Args:
            text (str): Raw text extracted from document.
            requested_fields (list[str]): Fields requested by client.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): Diagnosis metadata for context.

        Returns:
            dict: Extracted fields in snake_case.
        """
        if not text or not text.strip():
            Logger.warning("AiExtractor received empty text", document_type=document_type)
            return {}

        prompt = self._build_prompt(text, requested_fields, document_type, diagnosis, all_fields)

        Logger.info("Sending request to Groq API", document_type=document_type, model=Config.GROQ_MODEL)

        response = self._call_groq(prompt)
        extracted = self._parse_response(response)

        Logger.info("AiExtractor completed", fields_extracted=len([v for v in extracted.values() if v is not None]))

        return self._filter_fields(extracted, requested_fields)

    def _build_prompt(self, text: str, requested_fields: list[str], document_type: str, diagnosis: dict, all_fields: bool = False) -> str:
        """
        Build the extraction prompt with document context.

        Args:
            text (str): Raw document text.
            requested_fields (list[str]): Fields to extract.
            document_type (str): Document type identifier.
            diagnosis (dict): OCR/processing diagnosis metadata.

        Returns:
            str: Formatted prompt string.
        """
        if all_fields:
            fields_str = "all fields you can find in the document"
        else:
            fields_str = ", ".join(requested_fields) if requested_fields else "all available fields"

        confidence = diagnosis.get("confidence", "unknown") if diagnosis else "unknown"
        reason = diagnosis.get("reason", "unknown") if diagnosis else "unknown"

        return f"""You are a data extraction specialist for Mexican documents.
            Document type: {document_type or "unknown"}
            OCR quality: {reason} (confidence: {confidence})
            Fields to extract: {fields_str}

            Instructions:
            - Extract ONLY the requested fields from the text below.
            - If a field is not found, return null for that field.
            - Return ONLY a valid JSON object, no explanations, no markdown, no code blocks.
            - All field names must be in snake_case.
            - Text may contain OCR errors, do your best to interpret correctly.

            Text:
            {text}"""

    def _call_groq(self, prompt: str) -> str:
        """
        Send prompt to Groq API and return raw response text.

        Args:
            prompt (str): Formatted prompt to send.

        Returns:
            str: Raw response content from the model.

        Raises:
            RuntimeError: If the API call fails.
        """
        headers = {
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": Config.GROQ_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        response = requests.post(IA_API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            Logger.error("Groq API error", status=response.status_code, detail=response.text)
            raise RuntimeError(f"Groq API returned {response.status_code}: {response.text}")

        return response.json()["choices"][0]["message"]["content"]

    def _parse_response(self, raw: str) -> dict:
        """
        Parse JSON response from the model.

        Args:
            raw (str): Raw string response from the model.

        Returns:
            dict: Parsed fields or empty dict on failure.
        """
        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError) as e:
            Logger.error("Failed to parse AI response", detail=str(e), raw=raw[:200])
            return {}