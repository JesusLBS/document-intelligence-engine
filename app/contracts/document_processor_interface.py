from abc import ABC, abstractmethod


class DocumentProcessorInterface(ABC):
    """Document processor contract."""

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