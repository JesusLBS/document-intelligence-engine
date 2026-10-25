from abc import ABC, abstractmethod

from PIL import Image


class BaseOcr(ABC):
    """Base class for all OCR implementations."""

    @abstractmethod
    def extract_text(self, pages: list[Image.Image]) -> str:
        """
        Recognize the text of rendered page images.

        Args:
            pages (list[Image.Image]): Page images, in page order (rendered by the document processor).

        Returns:
            str: Recognized text.
        """
        pass
