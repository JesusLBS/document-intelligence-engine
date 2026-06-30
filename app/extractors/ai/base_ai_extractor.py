from abc import ABC, abstractmethod


class BaseAiExtractor(ABC):
    """Base contract for all AI provider extractors."""

    @abstractmethod
    def extract(self, text: str, requested_fields: list[str], document_type: str = None, diagnosis: dict = None, all_fields: bool = False) -> dict:
        """
        Extract fields using an AI provider.

        Args:
            text (str): Raw text from document.
            requested_fields (list[str]): Fields to extract.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): OCR diagnosis metadata.
            all_fields (bool): If True, extract all available fields.

        Returns:
            dict: Extracted fields in snake_case.
        """
        pass 

    def _build_prompt(self, text: str, requested_fields: list[str], document_type: str, diagnosis: dict, all_fields: bool = False) -> str:
        """
        Build extraction prompt — shared across all providers.

        Args:
            text (str): Raw document text.
            requested_fields (list[str]): Fields to extract.
            document_type (str): Document type identifier.
            diagnosis (dict): OCR diagnosis metadata.
            all_fields (bool): If True, extract everything found.

        Returns:
            str: Formatted prompt.
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

    def _parse_response(self, raw: str) -> dict:
        """
        Parse JSON response from AI model.

        Args:
            raw (str): Raw string response.

        Returns:
            dict: Parsed fields or empty dict on failure.
        """
        import json
        from app.helpers.logger import Logger

        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError) as e:
            Logger.error("Failed to parse AI response", detail=str(e), raw=raw[:200])
            return {}