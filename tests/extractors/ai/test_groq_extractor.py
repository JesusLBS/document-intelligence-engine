import pytest

from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException, AiProviderNotConfiguredException
from app.extractors.ai.groq_extractor import GroqExtractor
from tests.extractors.ai.conftest import FakeResponse


def groq_body(content: str, finish_reason: str = "stop") -> dict:
    """Build a chat completions response."""
    return {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    """A configured Groq provider on a reasoning model."""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(Config, "GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setattr(Config, "GROQ_REASONING_EFFORT", "low")


def extract(text: str = "OCR text") -> dict:
    return GroqExtractor().extract(text, ["curp"])


class TestGroqRequest:
    """The request matches Groq's chat completions contract for gpt-oss."""

    def test_payload_uses_json_mode_and_reasoning_params(self, fake_post):
        fake_post.response = FakeResponse(200, groq_body('{"curp": "X"}'))

        extract()

        payload = fake_post.calls[0]["json"]
        assert payload["model"] == "openai/gpt-oss-120b"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["reasoning_effort"] == "low"
        assert payload["include_reasoning"] is False
        assert payload["max_completion_tokens"] == GroqExtractor.MAX_COMPLETION_TOKENS
        assert "max_tokens" not in payload

    def test_empty_reasoning_effort_omits_reasoning_params(self, fake_post, monkeypatch):
        monkeypatch.setattr(Config, "GROQ_REASONING_EFFORT", "")
        fake_post.response = FakeResponse(200, groq_body("{}"))

        extract()

        payload = fake_post.calls[0]["json"]
        assert "reasoning_effort" not in payload
        assert "include_reasoning" not in payload

    def test_missing_api_key_fails_before_calling(self, fake_post, monkeypatch):
        monkeypatch.setattr(Config, "GROQ_API_KEY", "")

        with pytest.raises(AiProviderNotConfiguredException):
            extract()

        assert fake_post.calls == []

    def test_empty_text_skips_the_call(self, fake_post):
        assert extract(text="") == {}
        assert fake_post.calls == []


class TestGroqResponse:
    """Answers are parsed strictly; failures become clear 502 errors."""

    def test_json_answer_is_parsed(self, fake_post):
        fake_post.response = FakeResponse(200, groq_body('{"curp": "XAXX010101HDFAAA09"}'))

        assert extract() == {"curp": "XAXX010101HDFAAA09"}

    def test_http_error_becomes_502(self, fake_post):
        fake_post.response = FakeResponse(400, {"error": {"message": "model decommissioned"}}, text="decommissioned")

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 502

    def test_rate_limit_uses_retry_after_header(self, fake_post):
        body = {"error": {"message": "Rate limit reached ...", "type": "tokens", "code": "rate_limit_exceeded"}}
        fake_post.response = FakeResponse(429, body, headers={"retry-after": "7"})

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 503
        assert error.value.message == "AI provider 'groq' failed: exceeded its quota (rate_limit_exceeded); retry in 7s"

    def test_empty_answer_reports_finish_reason(self, fake_post):
        fake_post.response = FakeResponse(200, groq_body("", finish_reason="length"))

        with pytest.raises(AiProviderException) as error:
            extract()

        assert "finish_reason=length" in error.value.message

    def test_json_array_is_rejected(self, fake_post):
        fake_post.response = FakeResponse(200, groq_body('["not", "an", "object"]'))

        with pytest.raises(AiProviderException):
            extract()
