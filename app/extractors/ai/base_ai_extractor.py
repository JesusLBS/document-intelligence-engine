import json
import re
from abc import ABC, abstractmethod

import requests

from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException, AiProviderNotConfiguredException
from app.helpers.logger import Logger


# Optional markdown fence some models still wrap JSON in, even in JSON mode.
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class BaseAiExtractor(ABC):
    """Base contract for all AI provider extractors."""

    # Provider name used in errors and logs (e.g. 'gemini'); set by each subclass.
    provider_name: str = "ai"
    # True for providers that read the document file itself (PDF / image), not only its text.
    accepts_document_file: bool = False

    @abstractmethod
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
        Extract fields using an AI provider.

        Args:
            text (str): Raw text from document.
            requested_fields (list[str]): Fields to extract.
            document_type (str, optional): Document type for context.
            diagnosis (dict, optional): OCR diagnosis metadata.
            all_fields (bool): If True, extract all available fields.
            document_file (str, optional): File with only the requested pages (providers that read documents).
            document_mime_type (str, optional): Media type of document_file (e.g. 'application/pdf').
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

        definitions = self._field_definitions(document_type, requested_fields, all_fields)

        return f"""You are a data extraction specialist for Mexican documents.
Document type: {document_type or "unknown"}
OCR quality: {reason} (confidence: {confidence})
Fields to extract: {fields_str}
{definitions}{curp_hint}
Instructions:
- Extract ONLY the requested fields from the document below.
- If a field is not found, return null for that field.
- Return ONLY a valid JSON object, no explanations, no markdown, no code blocks.
- All field names must be in snake_case.
- If the document itself is attached, use it as the primary source of truth: the text below may be out of order
  (embedded PDF text) or contain character errors (OCR).
- The text below is a reference aid and may be incomplete.

Document text reference:
{text}"""

    def _field_definitions(self, document_type: str, requested_fields: list[str], all_fields: bool) -> str:
        """
        Describe the meaning and format of the requested fields known for this document type.

        Args:
            document_type (str): Document type identifier.
            requested_fields (list[str]): Fields to extract.
            all_fields (bool): If True, describe every known field of the type.

        Returns:
            str: Prompt section, or an empty string when no requested field has a description.
        """
        descriptions = Config.DOCUMENT_FIELD_DESCRIPTIONS.get(document_type, {})
        names = list(descriptions) if all_fields else [name for name in requested_fields if name in descriptions]
        if not names:
            return ""

        lines = "\n".join(f"- {name}: {descriptions[name]}" for name in names)
        return f"""
Field definitions (use exactly these keys and formats):
{lines}
"""

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
            AiProviderException: 504 on timeout; 503 when the key is rejected (401/403), a quota or
                rate limit is hit (429, with the limit and wait time) or the provider is overloaded (503);
                502 on connection errors and any other status.
        """
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.Timeout as e:
            raise AiProviderException(self.provider_name, f"timed out after {timeout}s", status_code=504) from e
        except requests.RequestException as e:
            raise AiProviderException(self.provider_name, "could not reach the API") from e

        status = response.status_code
        if status == 429:
            # Quota / rate limit, not an outage: say which limit and when it resets.
            reason = self._rate_limit_reason(response)
            Logger.error("AI provider rate limit", provider=self.provider_name, status=status, reason=reason)
            raise AiProviderException(self.provider_name, reason, status_code=503)

        if status != 200:
            # Provider error bodies describe the request problem, not the document; still truncated.
            Logger.error("AI provider HTTP error", provider=self.provider_name, status=status, detail=response.text[:300])

            if status in (401, 403):
                raise AiProviderException(self.provider_name, f"rejected the API key (HTTP {status})", status_code=503)
            if status == 503:
                raise AiProviderException(
                    self.provider_name, f"is temporarily unavailable (HTTP {status}), try again later", status_code=503
                )
            raise AiProviderException(self.provider_name, f"API returned HTTP {status}")

        try:
            return response.json()
        except ValueError as e:
            raise AiProviderException(self.provider_name, "API returned a non-JSON body") from e

    @staticmethod
    def _rate_limit_reason(response) -> str:
        """
        Describe a 429: which quota was exceeded and how long until it resets, when the provider says.

        Reads Gemini's google.rpc details (QuotaFailure, RetryInfo) and the Retry-After header /
        error code that Groq (OpenAI-compatible) sends. Never includes the provider's free-text message.

        Args:
            response (requests.Response): The 429 response.

        Returns:
            str: Client-safe reason, e.g. "exceeded its quota (GenerateRequestsPerDay..., limit 20); retry in ~8.9 h".
        """
        try:
            error = response.json().get("error") or {}
        except ValueError:
            error = {}

        quota = None
        retry_seconds = None
        for detail in error.get("details") or []:
            detail_type = detail.get("@type", "")
            if detail_type.endswith("QuotaFailure"):
                violation = (detail.get("violations") or [{}])[0]
                quota_id = violation.get("quotaId")
                if quota_id:
                    limit = violation.get("quotaValue")
                    quota = f"{quota_id}, limit {limit}" if limit else quota_id
            elif detail_type.endswith("RetryInfo"):
                delay = str(detail.get("retryDelay", "")).rstrip("s")
                retry_seconds = float(delay) if delay.replace(".", "", 1).isdigit() else None

        if retry_seconds is None:
            header = response.headers.get("retry-after", "") if response.headers else ""
            retry_seconds = float(header) if header.replace(".", "", 1).isdigit() else None

        if quota is None and isinstance(error.get("code"), str):
            quota = error["code"]  # Groq: e.g. "rate_limit_exceeded"

        reason = f"exceeded its quota ({quota})" if quota else "exceeded its quota or rate limit (HTTP 429)"
        if retry_seconds is None:
            reason = f"{reason}; try again later"
        elif retry_seconds < 120:
            reason = f"{reason}; retry in {retry_seconds:.0f}s"
        elif retry_seconds < 7200:
            reason = f"{reason}; retry in ~{retry_seconds / 60:.0f} min"
        else:
            # Only an estimate: on 2026-10-25 Gemini said ~8.9 h and accepted a call 83 s later.
            reason = f"{reason}; retry in ~{retry_seconds / 3600:.1f} h"

        if quota and "freetier" in quota.lower():
            reason = f"{reason} (free tier: use the other provider or a paid plan for more requests)"
        return reason

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
