class AppException(Exception):
    """Base exception for all custom application errors."""

    status_code: int = 500
    message: str = "An unexpected error has occurred"

    def __init__(self, message: str = None, status_code: int = None):
        """
        Initialize the application exception.

        Args:
            message (str, optional): Override default message.
            status_code (int, optional): Override default HTTP status code.
        """
        self.message = message or self.message
        self.status_code = status_code or self.status_code
        super().__init__(self.message)