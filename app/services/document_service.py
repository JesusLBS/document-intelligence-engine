import os

from werkzeug.datastructures import FileStorage

from app.factories.document_processor_factory import DocumentProcessorFactory


UPLOAD_FOLDER = "uploads"


class DocumentService:
    """Orchestrates document processing flow."""

    def process(self, file: FileStorage) -> dict:
        """
        Save and process an uploaded document.
        File is already validated at route level.

        Args:
            file (FileStorage): Validated uploaded file.

        Returns:
            dict: Processing result data.

        Raises:
            RuntimeError: Propagated from processor on failure.
        """
        extension = self._get_extension(file.filename)
        file_path = self._save(file, extension)

        try:
            processor = DocumentProcessorFactory.make(extension)
            return processor.process(file_path)
        finally:
            self._cleanup(file_path)

    def _get_extension(self, filename: str) -> str:
        """
        Extract and return lowercase file extension.

        Args:
            filename (str): Original filename.

        Returns:
            str: Lowercase extension without dot.
        """
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    def _save(self, file: FileStorage, extension: str) -> str:
        """
        Save uploaded file to the uploads folder.

        Args:
            file (FileStorage): File to save.
            extension (str): File extension used for naming.

        Returns:
            str: Absolute path to the saved file.
        """
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, f"temp_{os.getpid()}.{extension}")
        file.save(file_path)
        return file_path

    def _cleanup(self, file_path: str) -> None:
        """
        Delete temporary file after processing.

        Args:
            file_path (str): Path to the file to remove.
        """
        if os.path.exists(file_path):
            os.remove(file_path)