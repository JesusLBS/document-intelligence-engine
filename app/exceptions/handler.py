from flask import Flask

from app.exceptions.app_exception import AppException
from app.helpers.response_helper import ResponseHelper
from app.helpers.logger import Logger


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers on the Flask app.

    Args:
        app (Flask): Flask application instance.
    """

    @app.errorhandler(AppException)
    def handle_app_exception(e: AppException):
        """Handle known application exceptions with their own status code."""
        Logger.warning("Handled application exception", exception_type=type(e).__name__, detail=e.message)
        return ResponseHelper.error(message=e.message, status=e.status_code, exc=e)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        """Handle any unhandled exception as a 500 error."""
        Logger.error("Unhandled exception", exception_type=type(e).__name__, detail=str(e))
        return ResponseHelper.error(exc=e)