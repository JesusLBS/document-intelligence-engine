import logging

import pytest

from app.config import Config
from app.exceptions.ai_provider_exception import AiProviderException, AiProviderNotConfiguredException
from app.extractors.ai.gemini_extractor import GeminiExtractor
from tests.extractors.ai.conftest import FakeResponse


def gemini_body(*parts, finish_reason="STOP") -> dict:
    """Build a generateContent response with the given parts."""
    return {"candidates": [{"content": {"parts": list(parts)}, "finishReason": finish_reason}]}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    """A configured Gemini provider on a Gemini 3 model."""
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(Config, "GEMINI_MODEL", "gemini-3.6-flash")
    monkeypatch.setattr(Config, "GEMINI_THINKING_LEVEL", "low")


def extract(**kwargs) -> dict:
    return GeminiExtractor().extract(kwargs.pop("text", "OCR text"), kwargs.pop("fields", ["curp"]), **kwargs)


class TestGeminiRequest:
    """The request matches the current generateContent contract for Gemini 3."""

    def test_payload_uses_json_mode_and_thinking_level(self, fake_post):
        fake_post.response = FakeResponse(200, gemini_body({"text": '{"curp": "X"}'}))

        extract()

        call = fake_post.calls[0]
        config = call["json"]["generationConfig"]
        assert call["url"].endswith("/gemini-3.6-flash:generateContent")
        assert config["responseMimeType"] == "application/json"
        assert config["thinkingConfig"] == {"thinkingLevel": "low"}
        assert "temperature" not in config
        assert "thinkingBudget" not in str(config)
        assert call["timeout"] == Config.GEMINI_TIMEOUT_SECONDS

    def test_empty_thinking_level_omits_thinking_config(self, fake_post, monkeypatch):
        monkeypatch.setattr(Config, "GEMINI_THINKING_LEVEL", "")
        fake_post.response = FakeResponse(200, gemini_body({"text": "{}"}))

        extract()

        assert "thinkingConfig" not in fake_post.calls[0]["json"]["generationConfig"]

    def test_gemini_2_models_never_get_thinking_level(self, fake_post, monkeypatch):
        # gemini-2.5-flash answers 400 "Thinking level is not supported for this model".
        monkeypatch.setattr(Config, "GEMINI_MODEL", "gemini-2.5-flash")
        fake_post.response = FakeResponse(200, gemini_body({"text": "{}"}))

        extract()

        config = fake_post.calls[0]["json"]["generationConfig"]
        assert "thinkingConfig" not in config
        assert config["responseMimeType"] == "application/json"

    def test_document_file_is_sent_inline_with_its_mime_type(self, fake_post, tmp_path):
        import base64

        document = tmp_path / "pages.pdf"
        document.write_bytes(b"%PDF-1.7 fake")
        fake_post.response = FakeResponse(200, gemini_body({"text": "{}"}))

        extract(document_file=str(document), document_mime_type="application/pdf")

        parts = fake_post.calls[0]["json"]["contents"][0]["parts"]
        assert parts[1]["inline_data"]["mime_type"] == "application/pdf"
        assert base64.b64decode(parts[1]["inline_data"]["data"]) == b"%PDF-1.7 fake"

    def test_gemini_reads_document_files(self):
        assert GeminiExtractor.accepts_document_file is True

    def test_missing_api_key_fails_before_calling(self, fake_post, monkeypatch):
        monkeypatch.setattr(Config, "GEMINI_API_KEY", "")

        with pytest.raises(AiProviderNotConfiguredException) as error:
            extract()

        assert error.value.status_code == 503
        assert fake_post.calls == []

    def test_no_text_and_no_document_skips_the_call(self, fake_post):
        assert extract(text="   ") == {}
        assert fake_post.calls == []


class TestGeminiResponse:
    """Answers are parsed strictly; failures become clear 502/504 errors."""

    def test_json_answer_is_parsed(self, fake_post):
        fake_post.response = FakeResponse(200, gemini_body({"text": '{"curp": "XAXX010101HDFAAA09"}'}))

        assert extract() == {"curp": "XAXX010101HDFAAA09"}

    def test_thought_parts_are_ignored(self, fake_post):
        fake_post.response = FakeResponse(200, gemini_body(
            {"text": "reasoning about the card", "thought": True},
            {"text": '{"curp": "X"}'},
        ))

        assert extract() == {"curp": "X"}

    def test_fenced_json_is_parsed(self, fake_post):
        fake_post.response = FakeResponse(200, gemini_body({"text": '```json\n{"curp": "X"}\n```'}))

        assert extract() == {"curp": "X"}

    def test_http_error_becomes_502(self, fake_post):
        fake_post.response = FakeResponse(404, {"error": {"message": "model not found"}}, text="model not found")

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 502
        assert "HTTP 404" in error.value.message

    def test_overloaded_provider_becomes_503(self, fake_post):
        # Real case: gemini-3.6-flash answered 503 "experiencing high demand".
        fake_post.response = FakeResponse(503, {"error": {"message": "high demand"}}, text="high demand")

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 503
        assert "temporarily unavailable" in error.value.message

    def test_exhausted_quota_says_which_limit_and_when(self, fake_post):
        # Real case (2026-10-25): free tier allows 20 requests per day per model on gemini-3.6-flash.
        body = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota...",
                          "details": [
                              {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{
                                  "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}]},
                              {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "31927s"},
                          ]}}
        fake_post.response = FakeResponse(429, body)

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 503
        assert error.value.message == (
            "AI provider 'gemini' failed: exceeded its quota "
            "(GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit 20); retry in ~8.9 h "
            "(free tier: use the other provider or a paid plan for more requests)"
        )

    def test_429_without_details_still_reports_quota(self, fake_post):
        fake_post.response = FakeResponse(429, {"error": {"message": "slow down"}})

        with pytest.raises(AiProviderException) as error:
            extract()

        assert "exceeded its quota or rate limit (HTTP 429); try again later" in error.value.message

    @pytest.mark.parametrize("status", [401, 403])
    def test_rejected_key_becomes_503(self, fake_post, status):
        fake_post.response = FakeResponse(status, {"error": {"message": "Invalid API Key"}}, text="Invalid API Key")

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 503
        assert "rejected the API key" in error.value.message

    def test_timeout_becomes_504(self, fake_post, timeout_error):
        fake_post.error = timeout_error

        with pytest.raises(AiProviderException) as error:
            extract()

        assert error.value.status_code == 504

    def test_blocked_prompt_becomes_502(self, fake_post):
        fake_post.response = FakeResponse(200, {"promptFeedback": {"blockReason": "SAFETY"}})

        with pytest.raises(AiProviderException) as error:
            extract()

        assert "SAFETY" in error.value.message

    def test_truncated_empty_answer_reports_finish_reason(self, fake_post):
        fake_post.response = FakeResponse(200, gemini_body(finish_reason="MAX_TOKENS"))

        with pytest.raises(AiProviderException) as error:
            extract()

        assert "MAX_TOKENS" in error.value.message

    def test_invalid_json_fails_without_logging_document_data(self, fake_post, caplog):
        secret = "JUAN PEREZ LOPEZ XAXX010101HDFAAA09"
        fake_post.response = FakeResponse(200, gemini_body({"text": f"Sure! The name is {secret}"}))

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(AiProviderException):
                extract()

        assert secret not in caplog.text
        assert "XAXX010101HDFAAA09" not in caplog.text
