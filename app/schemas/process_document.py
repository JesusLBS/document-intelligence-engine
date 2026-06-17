from marshmallow import Schema, fields, validates, ValidationError
from werkzeug.datastructures import FileStorage

from app.config import Config


class ProcessDocumentSchema(Schema):
    """Validation schema for document processing endpoint."""

    file = fields.Raw(required=True)
    document_type = fields.Str(required=True)
    requested_fields = fields.List(fields.Str(), load_default=[], data_key="fields")
    extractor = fields.Str(load_default=Config.DEFAULT_EXTRACTOR)
    language = fields.Str(load_default=Config.DEFAULT_LANGUAGE)
    include_raw_text = fields.Bool(load_default=True)

    @validates("file")
    def validate_file(self, value):
        """
        Validate file type and size.

        Args:
            value: Uploaded FileStorage object.

        Raises:
            ValidationError: If file is invalid, wrong type or too large.
        """
        if not isinstance(value, FileStorage):
            raise ValidationError("A valid file must be uploaded.")

        if not value.filename:
            raise ValidationError("No file name provided.")

        ext = value.filename.rsplit(".", 1)[-1].lower() if "." in value.filename else ""

        if ext not in Config.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' is not allowed. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}."
            )

        value.stream.seek(0, 2)
        size_mb = value.stream.tell() / (1024 * 1024)
        value.stream.seek(0)

        if size_mb > Config.MAX_FILE_SIZE_MB:
            raise ValidationError(f"File exceeds the {Config.MAX_FILE_SIZE_MB}MB limit.")

    @validates("document_type")
    def validate_document_type(self, value):
        """
        Validate document type against registered types.

        Args:
            value (str): Document type sent by client.

        Raises:
            ValidationError: If document type is not registered.
        """
        if value not in Config.DOCUMENT_TYPES:
            raise ValidationError(
                f"Document type '{value}' is not supported. "
                f"Allowed: {', '.join(sorted(Config.DOCUMENT_TYPES))}."
            )