from marshmallow import Schema, fields, validate, validates, ValidationError
from werkzeug.datastructures import FileStorage

from app.validators.base_validator import validate as request_validate


ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE_MB = 10


class ProcessDocumentSchema(Schema):
    """Validation schema for document processing endpoint."""

    file = fields.Raw(required=True, metadata={"description": "Uploaded file (multipart/form-data)"})

    @validates("file")
    def validate_file(self, value):
        """
        Validate uploaded file type and size.

        Args:
            value: Value from request data for 'file' key.

        Raises:
            ValidationError: If file is invalid.
        """
        if not isinstance(value, FileStorage):
            raise ValidationError("A valid file must be uploaded.")

        if not value.filename or value.filename == "":
            raise ValidationError("No file name provided.")

        ext = value.filename.rsplit(".", 1)[-1].lower() if "." in value.filename else ""

        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"File type '{ext}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}.")

        # Check size
        value.stream.seek(0, 2)  # Seek to end
        size_mb = value.stream.tell() / (1024 * 1024)
        value.stream.seek(0)     # Reset

        if size_mb > MAX_FILE_SIZE_MB:
            raise ValidationError(f"File size exceeds the {MAX_FILE_SIZE_MB}MB limit.")


validate_process_document = request_validate(ProcessDocumentSchema())