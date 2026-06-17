from flask import request

from app.helpers.response_helper import ResponseHelper
from app.services.document_service import DocumentService
import json

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
        try:
            file = request.files.get("file")
            document_type = request.form.get("document_type")
            requested_fields = request.form.getlist("fields")
            include_raw_text = request.form.get("include_raw_text", "true").lower() == "true"

            result = self.document_service.process(file, document_type, requested_fields)

            if not include_raw_text:
                result["text"] = None

            return ResponseHelper.success(data=result)
        except Exception as e:
            return ResponseHelper.error(exc=e)