import io

import fitz  # PyMuPDF
import pytest

from index import app as flask_app


@pytest.fixture
def client():
    """Return a Flask test client for the real application."""
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


@pytest.fixture
def make_pdf():
    """
    Return a factory that builds an in-memory PDF with embedded (selectable) text.

    Embedded text makes PdfProcessor choose `text_extraction`, so tests exercise
    the real pipeline without needing Tesseract or AI providers.
    """
    def _make(text: str = "Sample document text for testing purposes.", pages: int = 1) -> bytes:
        doc = fitz.open()
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((50, 60), text, fontsize=9)
        data = doc.tobytes()
        doc.close()
        return data

    return _make


@pytest.fixture
def upload():
    """Return a helper that wraps bytes as a multipart file tuple for the test client."""
    def _upload(data: bytes, filename: str = "document.pdf") -> tuple:
        return (io.BytesIO(data), filename)

    return _upload
