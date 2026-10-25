import logging
import uuid

import pytest

from app.config import Config
from app.routes import routes
from index import MULTIPART_OVERHEAD_BYTES, app as flask_app


ENDPOINT = "/api/v1/documents/process"


class RecordingService:
    """Records the request id the controller sends to the service."""

    def __init__(self):
        self.request_ids = []

    def process(self, **kwargs) -> dict:
        self.request_ids.append(kwargs.get("request_id"))
        return {"text": None, "extractedFields": {}}


class TestUploadLimit:
    """Oversized requests are cut by Flask with a JSON 413 before being read."""

    def test_limit_follows_max_file_size(self):
        expected = Config.MAX_FILE_SIZE_MB * 1024 * 1024 + MULTIPART_OVERHEAD_BYTES
        assert flask_app.config["MAX_CONTENT_LENGTH"] == expected

    def test_oversized_request_returns_413(self, client, upload, monkeypatch):
        monkeypatch.setitem(flask_app.config, "MAX_CONTENT_LENGTH", 1024)

        response = client.post(ENDPOINT, data={"file": upload(b"x" * 4096), "document_type": "csf"})

        assert response.status_code == 413
        body = response.get_json()
        assert body["ok"] is False
        assert body["status"] == 413


class TestRequestId:
    """One id per request, shared by the response body, the header, the logs and the service."""

    def test_header_matches_meta(self, client):
        response = client.get("/api/v1/health")

        request_id = response.headers["X-Request-ID"]
        assert response.get_json()["meta"]["request_id"] == request_id
        uuid.UUID(request_id)

    def test_each_request_gets_a_new_id(self, client):
        first = client.get("/api/v1/health").headers["X-Request-ID"]
        second = client.get("/api/v1/health").headers["X-Request-ID"]

        assert first != second

    def test_service_receives_the_same_id(self, client, make_pdf, upload, monkeypatch):
        service = RecordingService()
        monkeypatch.setattr(routes.document_controller, "document_service", service)

        response = client.post(ENDPOINT, data={"file": upload(make_pdf()), "document_type": "csf"})

        assert service.request_ids == [response.headers["X-Request-ID"]]

    def test_logs_carry_the_id(self, client, caplog):
        with caplog.at_level(logging.WARNING):
            response = client.get("/api/v1/does-not-exist")

        assert f"request_id={response.headers['X-Request-ID']}" in caplog.text


class TestErrorDetailsByEnvironment:
    """meta.exception follows Config.APP_ENV, the single source of env settings."""

    @pytest.fixture
    def failing_service(self, monkeypatch):
        class Failing:
            def process(self, **kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(routes.document_controller, "document_service", Failing())

    def post(self, client, make_pdf, upload):
        return client.post(ENDPOINT, data={"file": upload(make_pdf()), "document_type": "csf"})

    def test_production_hides_exception_details(self, client, make_pdf, upload, failing_service, monkeypatch):
        monkeypatch.setattr(Config, "APP_ENV", "production")

        response = self.post(client, make_pdf, upload)

        assert response.status_code == 500
        assert "exception" not in response.get_json()["meta"]

    def test_local_shows_exception_details(self, client, make_pdf, upload, failing_service, monkeypatch):
        monkeypatch.setattr(Config, "APP_ENV", "local")

        response = self.post(client, make_pdf, upload)

        assert response.get_json()["meta"]["exception"]["type"] == "RuntimeError"
