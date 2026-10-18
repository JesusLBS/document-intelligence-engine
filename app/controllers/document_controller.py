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

    def process(self, validated: dict) -> tuple:
        """
        Handle document upload and processing.

        Args:
            validated (dict): Request data already deserialized by ProcessDocumentSchema
                (booleans and integers coerced, defaults applied).

        Returns:
            tuple: Flask JSON response and status code.
        """
        result = self.document_service.process(
            file=validated["file"],
            document_type=validated["document_type"],
            provider=validated["provider"],
            requested_fields=validated["requested_fields"],
            from_page=validated["from_page"],
            to_page=validated["to_page"],
            force_ocr=validated["force_ocr"],
            debug_mode=validated["debug_mode"],
            extractor_strategy=validated["extractor"],
            all_fields=validated["all_fields"],
        )

        if not validated["include_raw_text"]:
            result["text"] = None

        return ResponseHelper.success(data=result)
