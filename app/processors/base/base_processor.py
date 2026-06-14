from abc import ABC

from app.contracts.document_processor_interface import (
    DocumentProcessorInterface,
)


class BaseProcessor(
    DocumentProcessorInterface,
    ABC,
):
    """
    Base processor implementation.
    """

    def build_response(
        self,
        success: bool,
        data: dict | None = None,
        errors: list | None = None,
    ) -> dict:
        """
        Build standard response.

        Args:
            success (bool)
            data (dict | None)
            errors (list | None)

        Returns:
            dict
        """
        return {
            "success": success,
            "data": data or {},
            "errors": errors or [],
        }