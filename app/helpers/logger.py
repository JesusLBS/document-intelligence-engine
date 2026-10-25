import logging

from app.helpers.request_context import current_request_id


class Logger:
    """Thin wrapper around Python logging, mirroring Laravel's Log facade."""

    _logger = logging.getLogger("app")

    @staticmethod
    def debug(message: str, **context) -> None:
        """
        Log a debug-level message with optional context.

        Args:
            message (str): Log message.
            **context: Additional key-value context appended to the message.
        """
        Logger._logger.debug(Logger._format(message, context))

    @staticmethod
    def info(message: str, **context) -> None:
        """
        Log an info-level message with optional context.

        Args:
            message (str): Log message.
            **context: Additional key-value context appended to the message.
        """
        Logger._logger.info(Logger._format(message, context))

    @staticmethod
    def warning(message: str, **context) -> None:
        """
        Log a warning-level message with optional context.

        Args:
            message (str): Log message.
            **context: Additional key-value context appended to the message.
        """
        Logger._logger.warning(Logger._format(message, context))

    @staticmethod
    def error(message: str, **context) -> None:
        """
        Log an error-level message with optional context.

        Args:
            message (str): Log message.
            **context: Additional key-value context appended to the message.
        """
        Logger._logger.error(Logger._format(message, context))

    @staticmethod
    def _format(message: str, context: dict) -> str:
        """
        Append context dict as key=value pairs to the message, plus the current
        request id when logging inside a request.

        Args:
            message (str): Base log message.
            context (dict): Extra context to append.

        Returns:
            str: Formatted message with context.
        """
        request_id = current_request_id()
        if request_id:
            context = {"request_id": request_id, **context}
        if not context:
            return message
        extra = " ".join(f"{k}={v}" for k, v in context.items())
        return f"{message} | {extra}"