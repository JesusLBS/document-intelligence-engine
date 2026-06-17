from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """Base class for all document extractors."""

    @abstractmethod
    def extract(self, text: str, requested_fields: list[str]) -> dict:
        """
        Extract fields from raw text.

        Args:
            text (str): Raw text from document processor.
            requested_fields (list[str]): Fields requested by client. Empty means all.

        Returns:
            dict: Extracted fields in snake_case.
        """
        pass

    def _filter_fields(self, data: dict, requested_fields: list[str]) -> dict:
        """
        Filter extracted data to only requested fields.

        Args:
            data (dict): All extracted fields.
            requested_fields (list[str]): Fields to keep. Empty returns all.

        Returns:
            dict: Filtered fields.
        """
        if not requested_fields:
            return data
        return {k: v for k, v in data.items() if k in requested_fields}