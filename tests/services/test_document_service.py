import io
import os

from werkzeug.datastructures import FileStorage

from app.services.document_service import DocumentService


class TestTemporaryUploads:
    """Temporary upload files must never collide between requests."""

    def test_each_request_gets_its_own_file(self):
        service = DocumentService()
        first = FileStorage(stream=io.BytesIO(b"first"), filename="a.pdf")
        second = FileStorage(stream=io.BytesIO(b"second"), filename="b.pdf")

        first_path = service._save(first, "pdf", "request-1")
        second_path = service._save(second, "pdf", "request-2")

        try:
            assert first_path != second_path
            with open(first_path, "rb") as f:
                assert f.read() == b"first"
            with open(second_path, "rb") as f:
                assert f.read() == b"second"
        finally:
            service._cleanup(first_path)
            service._cleanup(second_path)

        assert not os.path.exists(first_path)
        assert not os.path.exists(second_path)


class RecordingExtractor:
    """Captures exactly what the service passes to the extractor."""

    def __init__(self):
        self.calls = []

    def extract(self, text, requested_fields, context=None):
        self.calls.append((text, requested_fields, context))
        return {"some_field": "value"}


class TestUniformExtractorCall:
    """The service calls every extractor the same way (no isinstance on concrete types)."""

    def test_extractor_receives_context(self, make_pdf, monkeypatch):
        from app.extractors.extraction_context import ExtractionContext
        from app.services import document_service

        extractor = RecordingExtractor()
        monkeypatch.setattr(document_service.ExtractorFactory, "make", staticmethod(lambda *args, **kwargs: extractor))

        result = DocumentService().process(
            file=FileStorage(stream=io.BytesIO(make_pdf("Embedded text " * 20)), filename="doc.pdf"),
            document_type="csf",
            requested_fields=["rfc"],
            all_fields=False,
            request_id="request-ctx",
        )

        text, fields, context = extractor.calls[0]
        assert "Embedded text" in text
        assert fields == ["rfc"]
        assert isinstance(context, ExtractionContext)
        assert context.document_type == "csf"
        assert context.diagnosis["reason"] == "embedded_text_found"
        assert context.image_paths == []
        assert result["extractedFields"] == {"someField": "value"}
