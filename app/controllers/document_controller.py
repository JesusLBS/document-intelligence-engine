from flask import request

from app.services.document_service import DocumentService


class DocumentController:
    """Handle incoming document requests."""

    def __init__(self):
        self.document_service = DocumentService()

    def health(self) -> dict:
        """
        Health check endpoint.

        Returns:
            dict
        """
        return self.document_service.health()

    def process(self) -> tuple[dict, int]:
        """
        Handle document upload and processing.

        Returns:
            tuple[dict, int]: JSON response and HTTP status code.
        """
        file = request.files.get("file")
        return self.document_service.process(file)