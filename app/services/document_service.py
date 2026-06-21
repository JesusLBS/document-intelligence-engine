import os
import uuid

from werkzeug.datastructures import FileStorage

from app.config import Config
from app.factories.document_processor_factory import DocumentProcessorFactory
from app.factories.extractor_factory import ExtractorFactory
from app.ocr.tesseract_ocr import TesseractOcr
from app.utils.case_converter import dict_to_camel_case
from app.extractors.ai_extractor import AiExtractor


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
        extractor_strategy: str = None,
        all_fields: bool = False,
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
            extractor_strategy (str): Extractor strategy ('regex' or 'ai').
            all_fields (bool): If True, extract all available fields ignoring defaults.

        Returns:
            dict: Processing result with extracted fields in camelCase.
        """
        extension = self._get_extension(file.filename)
        file_path = self._save(file, extension)
        request_id = str(uuid.uuid4())
        strategy = extractor_strategy or Config.DEFAULT_EXTRACTOR

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

            extractor = ExtractorFactory.make(document_type, extractor_strategy=strategy)
            raw_text = processor_result.get("text") or ""
            diagnosis = processor_result.get("diagnosis")

            # Resolve fields to extract
            if all_fields:
                fields_to_extract = []
            elif requested_fields:
                fields_to_extract = requested_fields
            else:
                fields_to_extract = Config.DOCUMENT_DEFAULT_FIELDS.get(document_type, [])

            if isinstance(extractor, AiExtractor):
                extracted = extractor.extract(
                    raw_text,
                    fields_to_extract,
                    document_type=document_type,
                    diagnosis=diagnosis,
                    all_fields=all_fields,
                )
            else:
                extracted = extractor.extract(raw_text, fields_to_extract)

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