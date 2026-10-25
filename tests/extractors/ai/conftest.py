import pytest
import requests

from app.extractors.ai import base_ai_extractor


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code: int = 200, body=None, text: str = "", headers: dict = None):
        self.status_code = status_code
        self._body = body
        self.text = text or ""
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body


class FakePost:
    """Replaces requests.post: records calls and returns a queued response or raises."""

    def __init__(self):
        self.calls = []
        self.response = FakeResponse(200, {})
        self.error = None

    def __call__(self, url, headers=None, json=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def fake_post(monkeypatch):
    """Patch the HTTP call used by every AI provider."""
    fake = FakePost()
    monkeypatch.setattr(base_ai_extractor.requests, "post", fake)
    return fake


@pytest.fixture
def timeout_error():
    """A requests timeout, as raised by requests.post."""
    return requests.Timeout("read timed out")
