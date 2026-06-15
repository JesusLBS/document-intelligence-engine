import os

from werkzeug.datastructures import FileStorage

from app.factories.document_processor_factory import DocumentProcessorFactory


ALLOWED_EXTENSIONS = {"pdf"}
UPLOAD_FOLDER = "uploads"


class DocumentService:
    """Orchestrates document processing flow."""

    def health(self) -> dict:
        """
        Return application health status.

        Returns:
            dict
        """
        return {
            "success": True,
            "message": "Document Intelligence Engine is running",
        }

    def process(self, file: FileStorage) -> tuple[dict, int]:
        """
        Validate, save and process an uploaded document.

        Args:
            file (FileStorage): Uploaded file from Flask request.

        Returns:
            tuple[dict, int]: Response payload and HTTP status code.
        """
        if not file or file.filename == "":
            return {"success": False, "errors": ["No file provided"]}, 400

        extension = self._get_extension(file.filename)

        if extension not in ALLOWED_EXTENSIONS:
            return {"success": False, "errors": [f"File type '{extension}' not supported"]}, 422

        file_path = self._save(file, extension)

        try:
            processor = DocumentProcessorFactory.make(extension)
            result = processor.process(file_path)
            status = 200 if result.get("success") else 422
            return result, status
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