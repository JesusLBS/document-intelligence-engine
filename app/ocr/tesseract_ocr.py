import os
import cv2
import numpy as np
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
        Preprocess image using OpenCV to improve OCR accuracy.
        Applies grayscale, denoising, contrast enhancement and rotation correction.

        Args:
            image (Image.Image): Raw page image.

        Returns:
            Image.Image: Preprocessed image ready for OCR.
        """

        # Convert PIL to OpenCV
        img = np.array(image)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Denoise
        img = cv2.fastNlMeansDenoising(img, h=30)

        # Contrast enhancement with CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img)

        # Binarization with Otsu threshold
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Rotation correction via deskew
        coords = np.column_stack(np.where(img < 128))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.5:
                h, w = img.shape
                center = (w // 2, h // 2)
                matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # Convert back to PIL
        return Image.fromarray(img)

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