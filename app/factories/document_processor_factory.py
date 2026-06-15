from app.contracts.document_processor_interface import DocumentProcessorInterface
from app.processors.pdf.pdf_processor import PdfProcessor

PROCESSOR_MAP = {
    "pdf": PdfProcessor,
}


class DocumentProcessorFactory:
    """Resolves the correct processor based on file type."""

    @staticmethod
    def make(file_type: str) -> DocumentProcessorInterface:
        """
        Return a processor instance for the given file type.

        Args:
            file_type (str): Lowercase file extension (e.g. 'pdf').

        Returns:
            DocumentProcessorInterface: Concrete processor instance.

        Raises:
            ValueError: If no processor is registered for the file type.
        """
        processor_class = PROCESSOR_MAP.get(file_type.lower())

        if not processor_class:
            raise ValueError(f"No processor registered for file type: '{file_type}'")

        return processor_class()
