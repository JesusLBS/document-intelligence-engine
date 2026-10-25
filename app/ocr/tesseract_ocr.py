import os
import shutil
import uuid

import pytesseract

from pdf2image import convert_from_path
from PIL import Image

from app.ocr.base_ocr import BaseOcr
from app.helpers.logger import Logger


DEBUG_FOLDER = "storage/debug"
# Debug folders kept on disk (one per request with debug_mode=true); older ones are pruned.
DEBUG_KEEP = 10
TEMP_IMAGE_FOLDER = "storage/temp_images"

# Rendering and preprocessing, measured on samples/pdf/ine_sample.pdf (a color INE photo on a
# white letter page), scoring OCR text by card labels and ID patterns found, and by how many
# fields a text-only AI extracted from it (2026-10-25):
#   - full page, grayscale (old pipeline): 0-3 of 14 points; text-only AI got 0/7 fields
#   - cropped to the content area: 9-10 points; text-only AI got 5-6/7 fields matching Gemini
#   - grayscale vs color made no real difference (color slightly better); Tesseract binarizes itself
#   - 400 DPI beat 300 DPI (only variant reading the clave de elector) for +0.4 s per page
OCR_DPI = 400
# Pixels darker than this count as content when looking for the area to crop.
CONTENT_THRESHOLD = 235
CROP_PADDING = 20

# Page segmentation modes: PSM 3 (automatic layout) first; PSM 11 (sparse text) as fallback
# when a page yields (almost) nothing.
PRIMARY_PSM = 3
FALLBACK_PSM = 11
MIN_PAGE_CHARS = 30


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
            dpi=OCR_DPI,
        )

        if debug_mode and request_id:
            self._prune_debug_folders(keep=request_id)

        text_parts = []
        image_paths = []
        temp_id = request_id or str(uuid.uuid4())

        for i, image in enumerate(images):
            processed = self._crop_to_content(image)

            if debug_mode and request_id:
                self._persist_page(processed, request_id, i + 1)

            # Multimodal AI providers get the same cropped color image: more detail on the
            # document and a smaller upload than the whole page.
            temp_path = self._persist_temp_page(processed, temp_id, i + 1)
            image_paths.append(temp_path)

            text, psm = self._recognize(processed)
            text_parts.append(text)
            Logger.info("OCR page processed", page=i + 1, chars=len(text.strip()), psm=psm)

        full_text = "\n".join(text_parts)
        Logger.info("OCR extraction completed", total_chars=len(full_text.strip()), images_generated=len(image_paths))

        return {"text": full_text, "image_paths": image_paths}

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

    def _crop_to_content(self, image: Image.Image) -> Image.Image:
        """
        Crop the page to the area that actually has content, keeping the original colors.

        A photographed ID card on a mostly white page defeats Tesseract's layout analysis;
        cropping to the card fixes it. On full-page documents the crop only trims margins.
        No grayscale conversion: measured, it did not help (see OCR_DPI notes).

        Args:
            image (Image.Image): Rendered page.

        Returns:
            Image.Image: Cropped page (the original image if the page is blank).
        """
        mask = image.convert("L").point(lambda pixel: 255 if pixel < CONTENT_THRESHOLD else 0)
        box = mask.getbbox()
        if not box:
            return image

        left, top, right, bottom = box
        return image.crop((
            max(left - CROP_PADDING, 0),
            max(top - CROP_PADDING, 0),
            min(right + CROP_PADDING, image.width),
            min(bottom + CROP_PADDING, image.height),
        ))

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

    def _prune_debug_folders(self, keep: str) -> None:
        """
        Keep only the most recent debug folders so storage/debug does not grow forever.

        Unlike wiping everything, this never deletes the folder of a request that is
        still running (its own, or a concurrent one among the most recent).

        Args:
            keep (str): Request id whose folder must survive regardless of age.
        """
        if not os.path.isdir(DEBUG_FOLDER):
            return

        folders = [
            os.path.join(DEBUG_FOLDER, name)
            for name in os.listdir(DEBUG_FOLDER)
            if name != keep and os.path.isdir(os.path.join(DEBUG_FOLDER, name))
        ]
        folders.sort(key=os.path.getmtime, reverse=True)

        # The current request will add one more folder, so keep DEBUG_KEEP - 1 previous ones.
        for folder in folders[DEBUG_KEEP - 1:]:
            shutil.rmtree(folder, ignore_errors=True)

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