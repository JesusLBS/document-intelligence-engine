from abc import ABC

from app.contracts.document_processor_interface import DocumentProcessorInterface


class BaseProcessor(DocumentProcessorInterface, ABC):
    """Base processor — raises on failure, returns clean data dict on success."""

    def process(self, file_path: str, from_page: int = None, to_page: int = None) -> dict:
        """
        Process document with optional page range.

        Args:
            file_path (str): Absolute path to the file.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).

        Returns:
            dict
        """
        raise NotImplementedError