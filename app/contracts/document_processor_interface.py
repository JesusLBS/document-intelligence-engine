from abc import ABC, abstractmethod

from PIL import Image


class DocumentProcessorInterface(ABC):
    """Document processor contract."""

    # Media type of the files written by export_pages (sent as-is to multimodal AI providers).
    mime_type: str = "application/octet-stream"

    @abstractmethod
    def process(self, file_path: str, from_page: int = None, to_page: int = None) -> dict:
        """
        Process document.

        Args:
            file_path (str): Absolute path to the file.
            from_page (int, optional): Start page (1-indexed). None means first page.
            to_page (int, optional): End page (1-indexed). None means last page.

        Returns:
            dict
        """
        pass

    @abstractmethod
    def render_pages(self, file_path: str, from_page: int = None, to_page: int = None) -> list[Image.Image]:
        """
        Render the requested pages as images (for OCR and debug snapshots).

        Args:
            file_path (str): Absolute path to the file.
            from_page (int, optional): Start page (1-indexed). None means first page.
            to_page (int, optional): End page (1-indexed). None means last page.

        Returns:
            list[Image.Image]: One image per page, in page order.
        """
        pass

    @abstractmethod
    def export_pages(self, file_path: str, output_path: str, from_page: int = None, to_page: int = None) -> str:
        """
        Write a copy of the document holding only the requested pages, in its original format.

        Args:
            file_path (str): Absolute path to the file.
            output_path (str): Where to write the copy.
            from_page (int, optional): Start page (1-indexed). None means first page.
            to_page (int, optional): End page (1-indexed). None means last page.

        Returns:
            str: output_path.
        """
        pass
