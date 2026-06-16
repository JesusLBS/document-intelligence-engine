from abc import ABC
from app.contracts.document_processor_interface import DocumentProcessorInterface


class BaseProcessor(DocumentProcessorInterface, ABC):
    """Base processor — raises on failure, returns clean data dict on success."""
    pass