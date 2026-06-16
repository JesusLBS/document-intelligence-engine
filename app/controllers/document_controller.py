from flask import request

from app.helpers.response_helper import ResponseHelper
from app.services.document_service import DocumentService


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
            result = self.document_service.process(file)
            return ResponseHelper.success(data=result)
        except Exception as e:
            return ResponseHelper.error(exc=e)