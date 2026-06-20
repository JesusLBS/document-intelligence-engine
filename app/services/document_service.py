import os
import uuid

from werkzeug.datastructures import FileStorage

from app.config import Config
from app.factories.document_processor_factory import DocumentProcessorFactory
from app.factories.extractor_factory import ExtractorFactory
from app.ocr.tesseract_ocr import TesseractOcr
from app.utils.case_converter import dict_to_camel_case


OCR_REASONS = {"low_text_density", "partial_text_extraction", "scanned_image_pdf",
               "text_rendered_as_paths", "corrupt_or_proprietary_encoding"}


class DocumentService:
    """Orchestrates document processing flow."""

    def process(
        self,
        file: FileStorage,
        document_type: str,
        requested_fields: list[str],
        from_page: int = None,
        to_page: int = None,
        force_ocr: bool = False,
        debug_mode: bool = False,
    ) -> dict:
        """
        Save, process and extract data from an uploaded document.

        Args:
            file (FileStorage): Validated uploaded file.
            document_type (str): Type of document (e.g. 'csf').
            requested_fields (list[str]): Fields requested by client.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).
            force_ocr (bool): Skip evaluation and use OCR directly.
            debug_mode (bool): Persist debug images to disk.

        Returns:
            dict: Processing result with extracted fields in camelCase.
        """
        extension = self._get_extension(file.filename)
        file_path = self._save(file, extension)
        request_id = str(uuid.uuid4())

        try:
            processor = DocumentProcessorFactory.make(extension)
            processor_result = processor.process(file_path, from_page=from_page, to_page=to_page)

            needs_ocr = force_ocr or processor_result.get("processingMethod") == "ocr_required"
            processor_result["ocrRequired"] = needs_ocr

            if needs_ocr:
                ocr = TesseractOcr()
                ocr_text = ocr.extract_text(
                    file_path,
                    from_page=from_page,
                    to_page=to_page,
                    debug_mode=debug_mode,
                    request_id=request_id,
                )
                processor_result["text"] = ocr_text
                processor_result["processingMethod"] = "ocr"

            extractor = ExtractorFactory.make(document_type)
            raw_text = processor_result.get("text") or ""
            extracted = extractor.extract(raw_text, requested_fields)

            processor_result["extractedFields"] = dict_to_camel_case(extracted)
            return processor_result
        finally:
            self._cleanup(file_path)

    def _get_extension(self, filename: str) -> str:
        """
        Extract lowercase file extension.

        Args:
            filename (str): Original filename.

        Returns:
            str: Lowercase extension without dot.
        """
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _save(self, file: FileStorage, extension: str) -> str:
        """
        Save uploaded file temporarily to disk.

        Args:
            file (FileStorage): File to save.
            extension (str): File extension used for naming.

        Returns:
            str: Absolute path to the saved file.
        """
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(Config.UPLOAD_FOLDER, f"temp_{os.getpid()}.{extension}")
        file.save(file_path)
        return file_path

    def _cleanup(self, file_path: str) -> None:
        """
        Delete temporary file after processing.

        Args:
            file_path (str): Path to remove.
        """
        if os.path.exists(file_path):
            os.remove(file_path)