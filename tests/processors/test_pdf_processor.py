import pytest

from app.exceptions.app_exception import AppException
from app.exceptions.invalid_document_exception import InvalidDocumentException
from app.processors.pdf.pdf_processor import PdfProcessor


@pytest.fixture
def pdf_file(tmp_path, make_pdf):
    """Write a factory-built PDF to disk and return a path factory."""
    def _write(text: str = "Embedded text " * 20, pages: int = 1):
        path = tmp_path / "document.pdf"
        path.write_bytes(make_pdf(text, pages=pages))
        return str(path)

    return _write


class TestPdfProcessor:
    """PdfProcessor diagnosis and error handling on real (generated) PDFs."""

    def test_embedded_text_needs_no_ocr(self, pdf_file):
        result = PdfProcessor().process(pdf_file())

        assert result["processingMethod"] == "text_extraction"
        assert result["diagnosis"]["reason"] == "embedded_text_found"
        assert result["hasText"] is True

    def test_page_range_is_reported(self, pdf_file):
        result = PdfProcessor().process(pdf_file(pages=3), from_page=2, to_page=3)

        assert result["pages"] == 3
        assert result["processedPages"] == {"from": 2, "to": 3}

    def test_to_page_beyond_document_raises_422(self, pdf_file):
        with pytest.raises(AppException) as error:
            PdfProcessor().process(pdf_file(pages=1), to_page=5)

        assert error.value.status_code == 422

    def test_non_pdf_content_raises_invalid_document(self, tmp_path):
        path = tmp_path / "fake.pdf"
        path.write_bytes(b"plain text pretending to be a pdf")

        with pytest.raises(InvalidDocumentException) as error:
            PdfProcessor().process(str(path))

        assert error.value.status_code == 422
