import pytesseract

from PIL import Image

from app.ocr.base_ocr import BaseOcr
from app.helpers.logger import Logger


# Page segmentation modes: PSM 3 (automatic layout) first; PSM 11 (sparse text) as fallback
# when a page yields (almost) nothing.
PRIMARY_PSM = 3
FALLBACK_PSM = 11
MIN_PAGE_CHARS = 30


class TesseractOcr(BaseOcr):
    """OCR implementation using Tesseract via pytesseract."""

    def extract_text(self, pages: list[Image.Image]) -> str:
        """
        Recognize the text of already rendered pages (see app/processors/pdf/page_renderer.py).

        Args:
            pages (list[Image.Image]): Page images, in page order.

        Returns:
            str: Recognized text, one block per page.
        """
        text_parts = []

        for i, page in enumerate(pages):
            text, psm = self._recognize(page)
            text_parts.append(text)
            Logger.info("OCR page processed", page=i + 1, chars=len(text.strip()), psm=psm)

        full_text = "\n".join(text_parts)
        Logger.info("OCR extraction completed", total_chars=len(full_text.strip()), pages=len(pages))
        return full_text

    def _recognize(self, image: Image.Image) -> tuple[str, int]:
        """
        Run Tesseract with the primary layout mode, falling back to sparse-text mode
        when the page yields (almost) no text.

        Args:
            image (Image.Image): Cropped page image.

        Returns:
            tuple[str, int]: Recognized text and the PSM that produced it.
        """
        text = pytesseract.image_to_string(image, lang="spa", config=f"--psm {PRIMARY_PSM}")
        if len(text.strip()) >= MIN_PAGE_CHARS:
            return text, PRIMARY_PSM

        fallback = pytesseract.image_to_string(image, lang="spa", config=f"--psm {FALLBACK_PSM}")
        if len(fallback.strip()) > len(text.strip()):
            return fallback, FALLBACK_PSM

        return text, PRIMARY_PSM
