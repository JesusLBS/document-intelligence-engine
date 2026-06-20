from abc import ABC, abstractmethod


class BaseOcr(ABC):
    """Base class for all OCR implementations."""

    @abstractmethod
    def extract_text(self, file_path: str, from_page: int = None, to_page: int = None, debug_mode: bool = False, request_id: str = None) -> str:
        """
        Extract text from a file using OCR.

        Args:
            file_path (str): Absolute path to the file.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).
            debug_mode (bool): If True, persist page images to disk.
            request_id (str, optional): Used as subfolder name for debug images.

        Returns:
            str: Extracted text from all processed pages.
        """
        pass