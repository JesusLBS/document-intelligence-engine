import os
import uuid

from werkzeug.datastructures import FileStorage

from app.config import Config
from app.factories.document_processor_factory import DocumentProcessorFactory
from app.factories.extractor_factory import ExtractorFactory
from app.helpers.debug_store import DebugStore
from app.ocr.tesseract_ocr import TesseractOcr
from app.utils.case_converter import dict_to_camel_case
from app.utils.date_normalizer import normalize_dates
from app.utils.id_normalizer import normalize_identifiers
from app.extractors.extraction_context import ExtractionContext


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
        provider: str = None,
        request_id: str = None,
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
            debug_mode (bool): Save a snapshot of the request in storage/debug/{request_id}/
                (upload, page images, what the extractor received, result).
            extractor_strategy (str, optional): Extractor strategy ('regex' or 'ai'); defaults per document type.
            all_fields (bool): If True, extract all available fields.
            provider (str, optional): AI provider override ('gemini', 'groq').
            request_id (str, optional): Id of the HTTP request (names temp files and the debug folder);
                a new one is generated when called outside a request.

        Returns:
            dict: Processing result with extracted fields in camelCase.
        """
        extension = self._get_extension(file.filename)
        request_id = request_id or str(uuid.uuid4())
        file_path = self._save(file, extension, request_id)
        strategy = extractor_strategy or Config.default_extractor_for(document_type)
        document_file = None

        try:
            processor = DocumentProcessorFactory.make(extension)
            processor_result = processor.process(file_path, from_page=from_page, to_page=to_page)
            first_page = processor_result["processedPages"]["from"]

            needs_ocr = force_ocr or processor_result.get("processingMethod") == "ocr_required"
            processor_result["ocrRequired"] = needs_ocr

            # Pages are rendered once, only for the requested range, and only when something uses them.
            pages = processor.render_pages(file_path, from_page, to_page) if needs_ocr or debug_mode else []

            if needs_ocr:
                processor_result["text"] = TesseractOcr().extract_text(pages)
                processor_result["processingMethod"] = "ocr"

            extractor = ExtractorFactory.make(document_type, extractor_strategy=strategy, ai_provider=provider)

            # Providers that read documents (Gemini) get the file itself, cut to the requested pages,
            # whether it is digital or scanned; text-only extractors (Groq, regex) get the text.
            if extractor.accepts_document_file:
                document_file = processor.export_pages(
                    file_path, self._pages_path(request_id, extension), from_page, to_page
                )

            raw_text = processor_result.get("text") or ""
            diagnosis = processor_result.get("diagnosis")

            if all_fields:
                fields_to_extract = []
            elif requested_fields:
                fields_to_extract = requested_fields
            else:
                fields_to_extract = Config.DOCUMENT_DEFAULT_FIELDS.get(document_type, [])

            context = ExtractionContext(
                document_type=document_type,
                diagnosis=diagnosis,
                all_fields=all_fields,
                document_file=document_file,
                document_mime_type=processor.mime_type if document_file else None,
            )

            debug = None
            if debug_mode:
                # Saved before extracting, so a failing provider still leaves its input on disk.
                debug = DebugStore(request_id)
                debug.save_file(file_path, f"original.{extension}")
                debug.save_pages(pages, first_page)
                if document_file:
                    debug.save_file(document_file, f"sent_to_ai.{extension}")
                debug.save_text("extractor_text.txt", raw_text)
                debug.save_json("request.json", {
                    "request_id": request_id,
                    "document_type": document_type,
                    "extractor": type(extractor).__name__,
                    "provider": getattr(extractor, "provider", None),
                    "fields_to_extract": fields_to_extract,
                    "all_fields": all_fields,
                    "pages": {"total": processor_result.get("pages"), "processed": processor_result["processedPages"]},
                    "force_ocr": force_ocr,
                    "processing_method": processor_result["processingMethod"],
                    "diagnosis": diagnosis,
                    "sent_to_extractor": {
                        "text_chars": len(raw_text.strip()),
                        "document_file": f"sent_to_ai.{extension}" if document_file else None,
                        "document_mime_type": context.document_mime_type,
                    },
                })

            extracted = extractor.extract(raw_text, fields_to_extract, context)
            # Fix OCR look-alike errors in structured IDs (CURP, clave de elector), whatever the extractor.
            extracted = normalize_identifiers(extracted)
            # Dates in ISO (YYYY-MM-DD) even when the provider or OCR returns them as printed ("15 OCT 26").
            extracted = normalize_dates(extracted)

            if debug:
                debug.save_json("result.json", extracted)
                debug.log_saved()

            processor_result["extractedFields"] = dict_to_camel_case(extracted)
            return processor_result
        finally:
            self._cleanup(file_path)
            if document_file:
                self._cleanup(document_file)

    def _pages_path(self, request_id: str, extension: str) -> str:
        """
        Path of the temporary copy holding only the requested pages.

        Args:
            request_id (str): Unique id of the current request.
            extension (str): File extension.

        Returns:
            str: Path inside the upload folder.
        """
        return os.path.join(Config.UPLOAD_FOLDER, f"temp_{request_id}_pages.{extension}")

    def _get_extension(self, filename: str) -> str:
        """
        Extract lowercase file extension.

        Args:
            filename (str): Original filename.

        Returns:
            str: Lowercase extension without dot.
        """
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _save(self, file: FileStorage, extension: str, request_id: str) -> str:
        """
        Save uploaded file temporarily to disk under a per-request name.

        The name must be unique per request: the dev server handles requests in
        threads of the same process, so a per-process name would let concurrent
        uploads overwrite each other.

        Args:
            file (FileStorage): File to save.
            extension (str): File extension used for naming.
            request_id (str): Unique id of the current request.

        Returns:
            str: Path to the saved file.
        """
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(Config.UPLOAD_FOLDER, f"temp_{request_id}.{extension}")
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