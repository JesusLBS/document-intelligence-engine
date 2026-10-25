import pytest

from app.routes import routes
from tests.extractors.test_csf_extractor import SAMPLE_CSF_TEXT


ENDPOINT = "/api/v1/documents/process"


class FakeDocumentService:
    """Records the arguments the controller sends to the service."""

    def __init__(self):
        self.calls = []

    def process(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {"text": "raw text", "extractedFields": {}}


@pytest.fixture
def fake_service(monkeypatch):
    """Replace the controller's DocumentService with a recorder."""
    fake = FakeDocumentService()
    monkeypatch.setattr(routes.document_controller, "document_service", fake)
    return fake


class TestRequestValidation:
    """The schema rejects values the pipeline cannot handle with a 422."""

    def test_unknown_provider_returns_422(self, client, make_pdf, upload):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "ine",
            "extractor": "ai",
            "provider": "unknown-provider",
        })

        assert response.status_code == 422
        assert "provider" in response.get_json()["errors"]

    def test_unknown_extractor_returns_422(self, client, make_pdf, upload):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "csf",
            "extractor": "unknown-extractor",
        })

        assert response.status_code == 422
        assert "extractor" in response.get_json()["errors"]

    def test_unknown_document_type_returns_422(self, client, make_pdf, upload):
        response = client.post(ENDPOINT, data={"file": upload(make_pdf()), "document_type": "passport"})

        assert response.status_code == 422
        assert "document_type" in response.get_json()["errors"]


class TestControllerUsesValidatedData:
    """The controller forwards exactly what the schema accepted (coerced types, defaults)."""

    def test_numeric_booleans_are_coerced(self, client, make_pdf, upload, fake_service):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "csf",
            "force_ocr": "1",
            "debug_mode": "0",
            "all_fields": "1",
        })

        assert response.status_code == 200
        call = fake_service.calls[0]
        assert call["force_ocr"] is True
        assert call["debug_mode"] is False
        assert call["all_fields"] is True

    def test_include_raw_text_one_keeps_text(self, client, make_pdf, upload, fake_service):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "csf",
            "include_raw_text": "1",
        })

        assert response.get_json()["data"]["text"] == "raw text"

    def test_include_raw_text_zero_hides_text(self, client, make_pdf, upload, fake_service):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "csf",
            "include_raw_text": "0",
        })

        assert response.get_json()["data"]["text"] is None

    def test_bracket_fields_are_forwarded(self, client, make_pdf, upload, fake_service):
        client.post(ENDPOINT, data={
            "file": upload(make_pdf()),
            "document_type": "csf",
            "fields[]": ["rfc", "curp"],
        })

        assert fake_service.calls[0]["requested_fields"] == ["rfc", "curp"]

    def test_defaults_are_applied(self, client, make_pdf, upload, fake_service):
        client.post(ENDPOINT, data={"file": upload(make_pdf()), "document_type": "csf"})

        call = fake_service.calls[0]
        assert call["extractor_strategy"] == "regex"
        assert call["provider"] is None
        assert call["requested_fields"] == []
        assert call["from_page"] is None


class TestProcessPipeline:
    """End-to-end through the real service, processor and extractor (no OCR, no AI)."""

    def test_non_pdf_content_returns_422(self, client, upload):
        response = client.post(ENDPOINT, data={
            "file": upload(b"this is not a pdf", "fake.pdf"),
            "document_type": "csf",
        })

        assert response.status_code == 422
        assert "not a valid" in response.get_json()["message"]

    def test_page_range_beyond_document_returns_422(self, client, make_pdf, upload):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf(pages=1)),
            "document_type": "csf",
            "from_page": "3",
        })

        assert response.status_code == 422

    def test_csf_with_embedded_text_is_extracted(self, client, make_pdf, upload):
        response = client.post(ENDPOINT, data={
            "file": upload(make_pdf(SAMPLE_CSF_TEXT)),
            "document_type": "csf",
            "extractor": "regex",
            "include_raw_text": "false",
        })

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["processingMethod"] == "text_extraction"
        assert data["ocrRequired"] is False
        assert data["text"] is None
        assert data["extractedFields"]["rfc"] == "XAXX010101AAA"
        assert data["extractedFields"]["curp"] == "XAXX010101HDFAAA09"
