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

    accepts_document_file = False

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
        assert context.document_file is None
        assert result["extractedFields"] == {"someField": "value"}


class TestIdentifierNormalization:
    """Extracted CURP / clave de elector are corrected whatever extractor produced them."""

    def test_curp_with_ocr_look_alikes_is_fixed(self, make_pdf, monkeypatch):
        from app.services import document_service

        class OcrConfusedExtractor:
            accepts_document_file = False

            def extract(self, text, requested_fields, context=None):
                return {"curp": "XAXXO1O1O1HDFAAA09"}

        monkeypatch.setattr(document_service.ExtractorFactory, "make", staticmethod(lambda *a, **k: OcrConfusedExtractor()))

        result = DocumentService().process(
            file=FileStorage(stream=io.BytesIO(make_pdf("Embedded text " * 20)), filename="doc.pdf"),
            document_type="ine",
            requested_fields=["curp"],
        )

        assert result["extractedFields"]["curp"] == "XAXX010101HDFAAA09"


class StrategyRecorder:
    """Stands in for ExtractorFactory.make and records the strategy the service resolved."""

    def __init__(self, fields: dict = None):
        self.strategies = []
        self.fields = fields or {}

    def make(self, document_type, extractor_strategy=None, ai_provider=None):
        self.strategies.append(extractor_strategy)
        fields = self.fields

        class Extractor:
            accepts_document_file = False

            def extract(self, text, requested_fields, context=None):
                return dict(fields)

        return Extractor()


def process_comprobante(make_pdf, monkeypatch, recorder: StrategyRecorder) -> dict:
    from app.services import document_service

    monkeypatch.setattr(document_service.ExtractorFactory, "make", staticmethod(recorder.make))
    return DocumentService().process(
        file=FileStorage(stream=io.BytesIO(make_pdf("Embedded text " * 20)), filename="doc.pdf"),
        document_type="comprobante_domicilio",
        requested_fields=[],
    )


class TestAddressProof:
    """Comprobante de domicilio is AI-only and comes back with ISO dates."""

    def test_defaults_to_ai_without_explicit_strategy(self, make_pdf, monkeypatch):
        recorder = StrategyRecorder()

        process_comprobante(make_pdf, monkeypatch, recorder)

        assert recorder.strategies == ["ai"]

    def test_printed_dates_are_returned_as_iso(self, make_pdf, monkeypatch):
        recorder = StrategyRecorder({"fecha_emision": "14 OCT 26", "periodo_inicio": "12/08/2026", "proveedor": "X"})

        result = process_comprobante(make_pdf, monkeypatch, recorder)

        assert result["extractedFields"] == {"fechaEmision": "2026-10-14", "periodoInicio": "2026-08-12", "proveedor": "X"}


class DocumentReadingExtractor:
    """Stands in for Gemini: reads the document file; records what it received."""

    accepts_document_file = True

    def __init__(self):
        self.received = None

    def extract(self, text, requested_fields, context=None):
        import fitz

        with fitz.open(context.document_file) as doc:
            self.received = {
                "path": context.document_file,
                "mime_type": context.document_mime_type,
                "pages": [page.get_text().strip() for page in doc],
            }
        return {"proveedor": "X"}


def three_page_pdf() -> bytes:
    import fitz

    doc = fitz.open()
    for number in (1, 2, 3):
        doc.new_page().insert_text((50, 60), f"Page {number} " + "embedded text " * 20, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def process_with(extractor, monkeypatch, **kwargs) -> dict:
    from app.services import document_service

    monkeypatch.setattr(document_service.ExtractorFactory, "make", staticmethod(lambda *a, **k: extractor))
    return DocumentService().process(
        file=FileStorage(stream=io.BytesIO(three_page_pdf()), filename="doc.pdf"),
        document_type="comprobante_domicilio",
        requested_fields=[],
        **kwargs,
    )


class TestDocumentFileForAi:
    """Providers that read documents get the file itself, cut to the requested pages, even if digital."""

    def test_digital_pdf_is_sent_with_only_the_requested_pages(self, monkeypatch):
        extractor = DocumentReadingExtractor()

        process_with(extractor, monkeypatch, from_page=2, to_page=2, request_id="req-pages")

        assert extractor.received["mime_type"] == "application/pdf"
        assert len(extractor.received["pages"]) == 1
        assert extractor.received["pages"][0].startswith("Page 2")
        assert not os.path.exists(extractor.received["path"])  # temp copy removed afterwards

    def test_text_only_extractors_get_no_file(self, monkeypatch):
        extractor = RecordingExtractor()

        process_with(extractor, monkeypatch, from_page=1, to_page=1)

        text, _, context = extractor.calls[0]
        assert context.document_file is None
        assert text.startswith("Page 1") and "Page 2" not in text


class TestDebugSnapshot:
    """debug_mode saves the request for any document, with or without OCR."""

    def test_digital_pdf_without_ocr_is_saved(self, monkeypatch, tmp_path):
        import json

        from PIL import Image

        from app.helpers import debug_store
        from app.processors.pdf import page_renderer

        def convert_from_path(path, first_page=None, last_page=None, dpi=None):
            # CI has no poppler: stand in for pdf2image, one blank page per requested page.
            return [Image.new("RGB", (50, 50), "white") for _ in range(first_page, last_page + 1)]

        monkeypatch.setattr(debug_store, "DEBUG_FOLDER", str(tmp_path))
        monkeypatch.setattr(page_renderer, "convert_from_path", convert_from_path)

        process_with(DocumentReadingExtractor(), monkeypatch, from_page=2, to_page=3, debug_mode=True, request_id="req-debug")

        folder = tmp_path / "req-debug"
        assert sorted(p.name for p in folder.iterdir()) == [
            "extractor_text.txt", "original.pdf", "page_2.png", "page_3.png",
            "request.json", "result.json", "sent_to_ai.pdf",
        ]
        request = json.loads((folder / "request.json").read_text())
        assert request["processing_method"] == "text_extraction"
        assert request["pages"]["processed"] == {"from": 2, "to": 3}
        assert request["sent_to_extractor"]["document_mime_type"] == "application/pdf"
        assert json.loads((folder / "result.json").read_text()) == {"proveedor": "X"}

    def test_nothing_is_saved_without_debug_mode(self, monkeypatch, tmp_path):
        from app.helpers import debug_store

        monkeypatch.setattr(debug_store, "DEBUG_FOLDER", str(tmp_path))

        process_with(DocumentReadingExtractor(), monkeypatch, request_id="req-no-debug")

        assert list(tmp_path.iterdir()) == []


VALID_INE_FIELDS = {
    "nombre": "JUAN", "apellido_paterno": "PEREZ", "apellido_materno": "LOPEZ", "curp": "PELJ900515HDFRPN07",
    "fecha_nacimiento": "15/05/1990", "fecha_vencimiento": "2021-2031", "clave_elector": "PRLPJN90051509H000",
    "documento_detectado": "ine",
}


def process_ine(make_pdf, monkeypatch, requested_fields: list) -> dict:
    from app.services import document_service

    class IneExtractor:
        accepts_document_file = False

        def extract(self, text, requested_fields, context=None):
            return dict(VALID_INE_FIELDS)

    monkeypatch.setattr(document_service.ExtractorFactory, "make", staticmethod(lambda *a, **k: IneExtractor()))
    return DocumentService().process(
        file=FileStorage(stream=io.BytesIO(make_pdf("Embedded text " * 20)), filename="ine.pdf"),
        document_type="ine",
        requested_fields=requested_fields,
    )


class TestBusinessValidation:
    """Rules run on normalized fields after a full extraction (docs/decisions/0001)."""

    def test_full_extraction_is_validated_after_normalization(self, make_pdf, monkeypatch):
        result = process_ine(make_pdf, monkeypatch, requested_fields=[])

        # Printed formats were normalized before the rules ran, so the date rules could compare them.
        assert result["extractedFields"]["fechaNacimiento"] == "1990-05-15"
        assert result["extractedFields"]["fechaVencimiento"] == "2031"
        assert result["validation"]["valid"] is True
        assert result["validation"]["summary"]["failed"] == 0

    def test_custom_fields_are_not_validated(self, make_pdf, monkeypatch):
        result = process_ine(make_pdf, monkeypatch, requested_fields=["curp"])

        assert result["validation"] is None
        assert result["verdict"]["status"] == "not_validated"
        assert "custom fields" in result["verdict"]["message"]

    def test_full_extraction_returns_a_global_verdict(self, make_pdf, monkeypatch):
        result = process_ine(make_pdf, monkeypatch, requested_fields=[])

        assert result["verdict"]["status"] == "valid"
        assert result["verdict"]["documentType"] == "ine"

    def test_homoclave_o_from_ocr_no_longer_fails_the_birth_date_rule(self, make_pdf, monkeypatch):
        # Real INE case (2026-10-25), fictitious data: "O" for "0" at CURP position 17 passed the
        # check digit but contradicted the 1990 birth date; the app resolves it from the birth date.
        VALID_INE_FIELDS_WITH_O = {**VALID_INE_FIELDS, "curp": "PELJ900515HDFRPNO7"}
        monkeypatch.setitem(globals(), "VALID_INE_FIELDS", VALID_INE_FIELDS_WITH_O)

        result = process_ine(make_pdf, monkeypatch, requested_fields=[])

        assert result["extractedFields"]["curp"] == "PELJ900515HDFRPN07"
        assert result["verdict"]["status"] == "valid"
