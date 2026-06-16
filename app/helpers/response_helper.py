import os
import uuid
import traceback
from datetime import datetime, timezone

from flask import jsonify


class ResponseHelper:
    """Standardized API response helper."""

    DEFAULT_ERROR_MESSAGE = "An unexpected error has occurred"
    VALIDATION_MESSAGE = "The given data was invalid."

    @staticmethod
    def _get_env() -> str:
        """Return current APP_ENV from environment variables."""
        return os.environ.get("APP_ENV", "production")

    @staticmethod
    def _meta(exc: Exception = None) -> dict:
        """
        Build meta block with request context.

        Args:
            exc (Exception, optional): Exception for debug info.

        Returns:
            dict: Meta block.
        """
        env = ResponseHelper._get_env()

        meta = {
            "request_id": str(uuid.uuid4()),
            "env": env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if exc is not None and env != "production":
            tb = traceback.extract_tb(exc.__traceback__)
            last = tb[-1] if tb else None
            meta["exception"] = {
                "type": type(exc).__name__,
                "message": str(exc),
                "file": last.filename.split("/app/")[-1] if last else None,
                "line": last.lineno if last else None,
            }

        return meta

    @staticmethod
    def success(data: dict = None, status: int = 200) -> tuple:
        """
        Return a successful JSON response.

        Args:
            data (dict, optional): Response payload.
            status (int): HTTP status code.

        Returns:
            tuple: Flask JSON response and status code.
        """
        return jsonify({
            "ok": True,
            "status": status,
            "message": "Success request",
            "data": data or {},
            "meta": ResponseHelper._meta(),
        }), status

    @staticmethod
    def error(message: str = None, status: int = 500, exc: Exception = None) -> tuple:
        """
        Return a generic error JSON response.

        Args:
            message (str, optional): Error message override.
            status (int): HTTP status code.
            exc (Exception, optional): Caught exception for debug meta.

        Returns:
            tuple: Flask JSON response and status code.
        """
        return jsonify({
            "ok": False,
            "status": status,
            "message": message or ResponseHelper.DEFAULT_ERROR_MESSAGE,
            "meta": ResponseHelper._meta(exc),
        }), status

    @staticmethod
    def validation_error(errors: dict) -> tuple:
        """
        Return a 422 validation error response (Laravel-style).

        Args:
            errors (dict): Field-keyed validation errors from marshmallow.

        Returns:
            tuple: Flask JSON response and 422 status code.
        """
        return jsonify({
            "ok": False,
            "status": 422,
            "message": ResponseHelper.VALIDATION_MESSAGE,
            "errors": errors,
            "meta": ResponseHelper._meta(),
        }), 422