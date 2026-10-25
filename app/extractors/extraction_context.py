from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractionContext:
    """
    Per-request information an extractor may use beyond the raw text.

    Every extractor receives it through the same `extract()` signature, so the service
    never needs to know which concrete extractor it got. Regex extractors ignore it;
    AiExtractor uses it to build the prompt and send page images.
    """

    document_type: str | None = None
    diagnosis: dict | None = None
    all_fields: bool = False
    image_paths: list[str] = field(default_factory=list)
