from app.exceptions.app_exception import AppException


class ProcessorNotFoundException(AppException):
    """Raised when no processor is registered for a given file type."""

    status_code = 422

    def __init__(self, file_type: str):
        """
        Initialize with the unsupported file type.

        Args:
            file_type (str): File extension that has no registered processor.
        """
        super().__init__(message=f"No processor registered for file type: '{file_type}'")