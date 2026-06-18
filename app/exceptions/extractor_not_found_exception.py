from app.exceptions.app_exception import AppException


class ExtractorNotFoundException(AppException):
    """Raised when no extractor is registered for a given document type."""

    status_code = 422

    def __init__(self, document_type: str):
        """
        Initialize with the unsupported document type.

        Args:
            document_type (str): Document type that has no registered extractor.
        """
        super().__init__(message=f"No extractor registered for document type: '{document_type}'")