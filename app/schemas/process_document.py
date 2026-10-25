from marshmallow import Schema, fields, post_load, validate, validates, validates_schema, ValidationError
from werkzeug.datastructures import FileStorage

from app.config import Config


class ProcessDocumentSchema(Schema):
    """Validation schema for document processing endpoint."""

    file = fields.Raw(required=True)
    document_type = fields.Str(required=True)
    requested_fields = fields.List(fields.Str(), load_default=[], data_key="fields")
    # No load_default: the default depends on document_type (resolved in resolve_extractor).
    extractor = fields.Str(
        load_default=None,
        validate=validate.OneOf(sorted(Config.EXTRACTOR_STRATEGIES)),
    )
    include_raw_text = fields.Bool(load_default=True)
    from_page = fields.Int(load_default=None, allow_none=True)
    to_page = fields.Int(load_default=None, allow_none=True)
    force_ocr = fields.Bool(load_default=False)
    debug_mode = fields.Bool(load_default=False)
    all_fields = fields.Bool(load_default=False)
    provider = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(sorted(Config.AI_PROVIDERS)),
    )

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

    @validates_schema
    def validate_page_range(self, data, **kwargs):
        """
        Validate from_page and to_page logical consistency.

        Args:
            data (dict): Deserialized schema data.

        Raises:
            ValidationError: If page range is invalid.
        """
        from_page = data.get("from_page")
        to_page = data.get("to_page")

        if from_page is not None and from_page < 1:
            raise ValidationError({"from_page": ["Page number must be >= 1."]})

        if to_page is not None and to_page < 1:
            raise ValidationError({"to_page": ["Page number must be >= 1."]})

        if from_page and to_page and from_page > to_page:
            raise ValidationError({"from_page": ["from_page cannot be greater than to_page."]})

    @validates_schema
    def validate_extractor_for_type(self, data, **kwargs):
        """
        Reject extractor=regex for document types that have no regex extractor.

        Args:
            data (dict): Deserialized schema data.

        Raises:
            ValidationError: If regex is requested for an AI-only document type.
        """
        document_type = data.get("document_type")
        if data.get("extractor") == "regex" and document_type in Config.AI_ONLY_DOCUMENT_TYPES:
            raise ValidationError({"extractor": [f"Document type '{document_type}' only supports extractor 'ai'."]})

    @post_load
    def resolve_extractor(self, data, **kwargs):
        """
        Apply the per-type default extractor when the request does not send one.

        Args:
            data (dict): Deserialized schema data.

        Returns:
            dict: Data with `extractor` always set.
        """
        if data.get("extractor") is None:
            data["extractor"] = Config.default_extractor_for(data["document_type"])
        return data
