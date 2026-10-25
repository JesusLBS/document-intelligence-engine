import json
import re
from abc import ABC, abstractmethod

import requests

from app.exceptions.ai_provider_exception import AiProviderException, AiProviderNotConfiguredException
from app.helpers.logger import Logger


# Optional markdown fence some models still wrap JSON in, even in JSON mode.
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class BaseAiExtractor(ABC):
    """Base contract for all AI provider extractors."""

    # Provider name used in errors and logs (e.g. 'gemini'); set by each subclass.
    provider_name: str = "ai"

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

    def _require_api_key(self, api_key: str, env_var: str) -> None:
        """
        Fail fast when the provider API key is missing, instead of sending an unauthenticated request.

        Args:
            api_key (str): Configured API key.
            env_var (str): Environment variable name to mention in the error.

        Raises:
            AiProviderNotConfiguredException: If the key is empty.
        """
        if not api_key:
            raise AiProviderNotConfiguredException(self.provider_name, env_var)

    def _post_json(self, url: str, headers: dict, payload: dict, timeout: int) -> dict:
        """
        POST a JSON payload to the provider and return the decoded JSON body.

        Args:
            url (str): Provider endpoint.
            headers (dict): Request headers (auth included).
            payload (dict): JSON body.
            timeout (int): Seconds before giving up.

        Returns:
            dict: Decoded JSON response.

        Raises:
            AiProviderException: 504 on timeout; 503 when the key is rejected (401/403) or the
                provider is overloaded (429/503); 502 on connection errors and any other status.
        """
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.Timeout as e:
            raise AiProviderException(self.provider_name, f"timed out after {timeout}s", status_code=504) from e
        except requests.RequestException as e:
            raise AiProviderException(self.provider_name, "could not reach the API") from e

        status = response.status_code
        if status != 200:
            # Provider error bodies describe the request problem, not the document; still truncated.
            Logger.error("AI provider HTTP error", provider=self.provider_name, status=status, detail=response.text[:300])

            if status in (401, 403):
                raise AiProviderException(self.provider_name, f"rejected the API key (HTTP {status})", status_code=503)
            if status in (429, 503):
                raise AiProviderException(
                    self.provider_name, f"is temporarily unavailable (HTTP {status}), try again later", status_code=503
                )
            raise AiProviderException(self.provider_name, f"API returned HTTP {status}")

        try:
            return response.json()
        except ValueError as e:
            raise AiProviderException(self.provider_name, "API returned a non-JSON body") from e

    def _parse_response(self, raw: str) -> dict:
        """
        Parse the model's JSON answer into a dict of extracted fields.

        Never logs the raw answer: it contains document data (names, CURP, addresses).

        Args:
            raw (str): Model output text.

        Returns:
            dict: Extracted fields.

        Raises:
            AiProviderException: If the output is not a JSON object.
        """
        clean = _JSON_FENCE.sub("", raw or "").strip()

        try:
            data = json.loads(clean)
        except ValueError as e:
            Logger.error("AI response is not valid JSON", provider=self.provider_name, chars=len(clean))
            raise AiProviderException(self.provider_name, "returned an answer that is not valid JSON") from e

        if not isinstance(data, dict):
            raise AiProviderException(self.provider_name, "returned JSON that is not an object")

        return data
