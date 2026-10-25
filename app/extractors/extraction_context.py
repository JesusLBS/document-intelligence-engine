from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionContext:
    """
    Per-request information an extractor may use beyond the raw text.

    Every extractor receives it through the same `extract()` signature, so the service
    never needs to know which concrete extractor it got. Regex extractors ignore it;
    AiExtractor uses it to build the prompt and, for providers that read documents
    (Gemini), to send the file with only the requested pages.
    """

    document_type: str | None = None
    diagnosis: dict | None = None
    all_fields: bool = False
    document_file: str | None = None
    document_mime_type: str | None = None
