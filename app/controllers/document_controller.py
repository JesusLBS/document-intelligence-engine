from flask import request

from app.helpers.response_helper import ResponseHelper
from app.services.document_service import DocumentService
from app.config import Config

class DocumentController:
    """Handle incoming document requests."""

    def __init__(self):
        self.document_service = DocumentService()

    def health(self) -> tuple:
        """
        Health check endpoint.

        Returns:
            tuple: Flask JSON response and status code.
        """
        return ResponseHelper.success(
            data={"message": "Document Intelligence Engine is running"}
        )

    def process(self) -> tuple:
        """
        Handle document upload and processing.

        Returns:
            tuple: Flask JSON response and status code.
        """
        file = request.files.get("file")
        document_type = request.form.get("document_type")
        requested_fields = request.form.getlist("fields")
        include_raw_text = request.form.get("include_raw_text", "true").lower() == "true"
        force_ocr = request.form.get("force_ocr", "false").lower() == "true"
        debug_mode = request.form.get("debug_mode", "false").lower() == "true"

        from_page = request.form.get("from_page")
        to_page = request.form.get("to_page")
        from_page = int(from_page) if from_page else None
        to_page = int(to_page) if to_page else None
        extractor_strategy = request.form.get("extractor", Config.DEFAULT_EXTRACTOR)
        all_fields = request.form.get("all_fields", "false").lower() == "true"
        provider = request.form.get("provider", Config.AI_PROVIDER)

        result = self.document_service.process(
            file=file,
            document_type=document_type,
            provider=provider,
            requested_fields=requested_fields,
            from_page=from_page,
            to_page=to_page,
            force_ocr=force_ocr,
            debug_mode=debug_mode,
            extractor_strategy=extractor_strategy,
            all_fields=all_fields
        )

        if not include_raw_text:
            result["text"] = None

        return ResponseHelper.success(data=result)