from app.exceptions.app_exception import AppException


class InvalidDocumentException(AppException):
    """Raised when an uploaded file cannot be opened as the type its extension claims."""

    status_code = 422

    def __init__(self, file_type: str):
        """
        Initialize with the expected file type.

        Args:
            file_type (str): File type the upload claimed to be (e.g. 'pdf').
        """
        super().__init__(message=f"The uploaded file is not a valid or readable {file_type.upper()} document.")
