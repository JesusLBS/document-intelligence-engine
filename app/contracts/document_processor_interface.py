from abc import ABC, abstractmethod


class DocumentProcessorInterface(ABC):
    """
    Document processor contract.
    """

    @abstractmethod
    def process(self, file_path: str) -> dict:
        """
        Process document.

        Args:
            file_path (str)

        Returns:
            dict
        """
        pass