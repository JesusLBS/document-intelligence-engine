from abc import ABC, abstractmethod


class BaseAiExtractor(ABC):
    """Base contract for all AI provider extractors."""

    @abstractmethod
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
        Extract fields using an AI provider.

        Args:
            text (str): Raw text from document.
            requested_fields (list[str]): Fields to extract.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): OCR diagnosis metadata.
            all_fields (bool): If True, extract all available fields.
            image_paths (list[str], optional): Paths to page images for multimodal providers.
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            dict: Extracted fields in snake_case.
        """
        pass

    def _build_prompt(
        self,
        text: str,
        requested_fields: list[str],
        document_type: str,
        diagnosis: dict,
        all_fields: bool = False,
        name_hints: dict = None,
    ) -> str:
        """
        Build extraction prompt — shared across all providers.

        Args:
            text (str): Raw document text.
            requested_fields (list[str]): Fields to extract.
            document_type (str): Document type identifier.
            diagnosis (dict): OCR diagnosis metadata.
            all_fields (bool): If True, extract everything found.
            name_hints (dict, optional): Pre-decoded CURP name initials hints.

        Returns:
            str: Formatted prompt.
        """
        if all_fields:
            fields_str = "all fields you can find in the document"
        else:
            fields_str = ", ".join(requested_fields) if requested_fields else "all available fields"

        confidence = diagnosis.get("confidence", "unknown") if diagnosis else "unknown"
        reason = diagnosis.get("reason", "unknown") if diagnosis else "unknown"

        name_fields = {"nombre", "apellido_paterno", "apellido_materno"}
        needs_name_hint = all_fields or bool(name_fields & set(requested_fields))

        curp_hint = ""
        if needs_name_hint and name_hints:
            curp_hint = f"""
Name assignment hint (pre-decoded from CURP):
- apellido_paterno must start with: {name_hints["apellido_paterno_initial"]}
- apellido_materno must start with: {name_hints["apellido_materno_initial"]}
- nombre initial corresponds to: {name_hints["nombre_initial"]}
Note: {name_hints["note"]}
Use these initials to assign the correct value to each name field.
"""

        return f"""You are a data extraction specialist for Mexican documents.
Document type: {document_type or "unknown"}
OCR quality: {reason} (confidence: {confidence})
Fields to extract: {fields_str}
{curp_hint}
Instructions:
- Extract ONLY the requested fields from the document below.
- If a field is not found, return null for that field.
- Return ONLY a valid JSON object, no explanations, no markdown, no code blocks.
- All field names must be in snake_case.
- If an image is provided, use it as the primary source of truth since OCR text may contain errors.
- The OCR text below is a reference aid, may be incomplete or have character errors.

OCR text reference:
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