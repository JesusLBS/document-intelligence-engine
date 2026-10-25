from app.exceptions.app_exception import AppException


class AiProviderException(AppException):
    """Raised when an AI provider call fails (HTTP error, timeout, blocked or unparseable response)."""

    status_code = 502

    def __init__(self, provider: str, reason: str, status_code: int = None):
        """
        Initialize with the provider name and a short, client-safe reason.

        Args:
            provider (str): Provider name (e.g. 'gemini', 'groq').
            reason (str): Short description of the failure. Must never contain document content.
            status_code (int, optional): Override the HTTP status (e.g. 504 on timeout).
        """
        super().__init__(message=f"AI provider '{provider}' failed: {reason}", status_code=status_code)


class AiProviderNotConfiguredException(AppException):
    """Raised before calling a provider whose API key is not configured."""

    status_code = 503

    def __init__(self, provider: str, env_var: str):
        """
        Initialize with the provider name and the missing environment variable.

        Args:
            provider (str): Provider name (e.g. 'gemini').
            env_var (str): Environment variable that must be set (e.g. 'GEMINI_API_KEY').
        """
        super().__init__(message=f"AI provider '{provider}' is not configured: set {env_var} in .env.")
