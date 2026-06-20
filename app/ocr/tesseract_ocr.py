import os

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.ocr.base_ocr import BaseOcr
from app.helpers.logger import Logger


DEBUG_FOLDER = "storage/debug"


class TesseractOcr(BaseOcr):
    """OCR implementation using Tesseract via pytesseract."""

    def extract_text(
        self,
        file_path: str,
        from_page: int = None,
        to_page: int = None,
        debug_mode: bool = False,
        request_id: str = None,
    ) -> str:
        """
        Extract text from PDF pages using Tesseract OCR.

        Args:
            file_path (str): Absolute path to the PDF file.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).
            debug_mode (bool): If True, persist page images to disk.
            request_id (str, optional): Subfolder name for debug images.

        Returns:
            str: Extracted text from all processed pages.
        """
        Logger.info("Starting OCR extraction", file=file_path, from_page=from_page, to_page=to_page)

        images = convert_from_path(
            file_path,
            first_page=from_page,
            last_page=to_page,
            dpi=300,
        )

        if debug_mode and request_id:
            self._persist_images(images, request_id)

        text_parts = []
        for i, image in enumerate(images):
            processed = self._preprocess(image)
            text = pytesseract.image_to_string(processed, lang="spa")
            text_parts.append(text)
            Logger.info("OCR page processed", page=i + 1, chars=len(text.strip()))

        full_text = "\n".join(text_parts)
        Logger.info("OCR extraction completed", total_chars=len(full_text.strip()))

        return full_text

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.

        Args:
            image (Image.Image): Raw page image.

        Returns:
            Image.Image: Preprocessed grayscale image.
        """
        return image.convert("L")

    def _persist_images(self, images: list[Image.Image], request_id: str) -> None:
        """
        Save page images to debug folder for inspection.

        Args:
            images (list[Image.Image]): List of page images.
            request_id (str): Used as subfolder name.
        """
        debug_path = os.path.join(DEBUG_FOLDER, request_id)
        self._cleanup_previous(debug_path)
        os.makedirs(debug_path, exist_ok=True)

        for i, image in enumerate(images):
            image_path = os.path.join(debug_path, f"page_{i + 1}.png")
            image.save(image_path)
            Logger.info("Debug image saved", path=image_path)
    def _cleanup_previous(self, debug_path: str) -> None:
        """
        Remove all previous debug subfolders before persisting new ones.

        Args:
            debug_path (str): Path to current request debug subfolder (unused for cleanup scope).
        """
        if os.path.exists(DEBUG_FOLDER):
            for folder in os.listdir(DEBUG_FOLDER):
                folder_path = os.path.join(DEBUG_FOLDER, folder)
                if os.path.isdir(folder_path):
                    for f in os.listdir(folder_path):
                        os.remove(os.path.join(folder_path, f))
                    os.rmdir(folder_path)