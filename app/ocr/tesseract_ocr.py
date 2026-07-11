import os
import uuid

import pytesseract

from pdf2image import convert_from_path
from PIL import Image

from app.ocr.base_ocr import BaseOcr
from app.helpers.logger import Logger


DEBUG_FOLDER = "storage/debug"
TEMP_IMAGE_FOLDER = "storage/temp_images"


class TesseractOcr(BaseOcr):
    """OCR implementation using Tesseract via pytesseract."""

    def extract_text(
        self,
        file_path: str,
        from_page: int = None,
        to_page: int = None,
        debug_mode: bool = False,
        request_id: str = None,
    ) -> dict:
        """
        Extract text and generate page images from PDF pages using Tesseract OCR.

        Args:
            file_path (str): Absolute path to the PDF file.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).
            debug_mode (bool): If True, persist images to storage/debug for inspection.
            request_id (str, optional): Subfolder name for debug images.

        Returns:
            dict: {"text": str, "image_paths": list[str]}
        """
        Logger.info("Starting OCR extraction", file=file_path, from_page=from_page, to_page=to_page)

        images = convert_from_path(
            file_path,
            first_page=from_page,
            last_page=to_page,
            dpi=300,
        )

        if debug_mode and request_id:
            self._cleanup_previous()

        text_parts = []
        image_paths = []
        temp_id = request_id or str(uuid.uuid4())

        for i, image in enumerate(images):
            processed = self._preprocess(image)

            if debug_mode and request_id:
                self._persist_page(processed, request_id, i + 1)

            # Always save a temp copy so it can be sent to multimodal AI providers
            temp_path = self._persist_temp_page(image, temp_id, i + 1)
            image_paths.append(temp_path)

            text = pytesseract.image_to_string(processed, lang="spa")
            text_parts.append(text)
            Logger.info("OCR page processed", page=i + 1, chars=len(text.strip()))

        full_text = "\n".join(text_parts)
        Logger.info("OCR extraction completed", total_chars=len(full_text.strip()), images_generated=len(image_paths))

        return {"text": full_text, "image_paths": image_paths}

    def _preprocess(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.

        Args:
            image (Image.Image): Raw page image.

        Returns:
            Image.Image: Preprocessed grayscale image.
        """
        return image.convert("L")

    def _persist_page(self, image: Image.Image, request_id: str, page_number: int) -> None:
        """
        Save page image to debug folder for inspection.

        Args:
            image (Image.Image): Image to save.
            request_id (str): Used as subfolder name.
            page_number (int): Page number for filename.
        """
        debug_path = os.path.join(DEBUG_FOLDER, request_id)
        os.makedirs(debug_path, exist_ok=True)

        image_path = os.path.join(debug_path, f"page_{page_number}.png")
        image.save(image_path)
        Logger.info("Debug image saved", path=image_path)

    def _persist_temp_page(self, image: Image.Image, temp_id: str, page_number: int) -> str:
        """
        Save page image to a temp folder for use by multimodal AI providers.

        Args:
            image (Image.Image): Image to save.
            temp_id (str): Subfolder name (request id).
            page_number (int): Page number for filename.

        Returns:
            str: Absolute path to the saved image.
        """
        temp_path = os.path.join(TEMP_IMAGE_FOLDER, temp_id)
        os.makedirs(temp_path, exist_ok=True)

        image_path = os.path.join(temp_path, f"page_{page_number}.png")
        image.save(image_path)
        return image_path

    def _cleanup_previous(self) -> None:
        """Remove all previous debug subfolders before persisting new ones."""
        if os.path.exists(DEBUG_FOLDER):
            for folder in os.listdir(DEBUG_FOLDER):
                folder_path = os.path.join(DEBUG_FOLDER, folder)
                if os.path.isdir(folder_path):
                    for f in os.listdir(folder_path):
                        os.remove(os.path.join(folder_path, f))
                    os.rmdir(folder_path)

    @staticmethod
    def cleanup_temp_images(temp_id: str) -> None:
        """
        Remove temp images generated for AI processing after use.

        Args:
            temp_id (str): Subfolder name (request id) to remove.
        """
        temp_path = os.path.join(TEMP_IMAGE_FOLDER, temp_id)
        if os.path.exists(temp_path):
            for f in os.listdir(temp_path):
                os.remove(os.path.join(temp_path, f))
            os.rmdir(temp_path)