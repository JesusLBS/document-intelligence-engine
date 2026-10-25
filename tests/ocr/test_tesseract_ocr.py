import pytest
from PIL import Image

from app.ocr import tesseract_ocr
from app.ocr.tesseract_ocr import FALLBACK_PSM, MIN_PAGE_CHARS, PRIMARY_PSM, TesseractOcr


@pytest.fixture
def fake_tesseract(monkeypatch):
    """Patch pytesseract so each PSM returns a configured text and calls are recorded."""
    outputs = {}
    calls = []

    def image_to_string(image, lang=None, config=""):
        psm = int(config.split("--psm ")[1])
        calls.append(psm)
        return outputs.get(psm, "")

    monkeypatch.setattr(tesseract_ocr.pytesseract, "image_to_string", image_to_string)
    return outputs, calls


@pytest.fixture
def page():
    return Image.new("L", (100, 100), color=255)


class TestPsmFallback:
    """Sparse-text mode rescues pages where automatic layout finds nothing (e.g. ID cards)."""

    def test_primary_result_is_kept_when_long_enough(self, fake_tesseract, page):
        outputs, calls = fake_tesseract
        outputs[PRIMARY_PSM] = "x" * MIN_PAGE_CHARS

        text, psm = TesseractOcr()._recognize(page)

        assert psm == PRIMARY_PSM
        assert calls == [PRIMARY_PSM]

    def test_falls_back_to_sparse_mode_when_primary_is_empty(self, fake_tesseract, page):
        outputs, calls = fake_tesseract
        outputs[PRIMARY_PSM] = ""
        outputs[FALLBACK_PSM] = "INSTITUTO NACIONAL ELECTORAL CREDENCIAL PARA VOTAR"

        text, psm = TesseractOcr()._recognize(page)

        assert psm == FALLBACK_PSM
        assert "CREDENCIAL" in text
        assert calls == [PRIMARY_PSM, FALLBACK_PSM]

    def test_keeps_primary_when_fallback_is_not_better(self, fake_tesseract, page):
        outputs, _ = fake_tesseract
        outputs[PRIMARY_PSM] = "short"
        outputs[FALLBACK_PSM] = ""

        text, psm = TesseractOcr()._recognize(page)

        assert (text, psm) == ("short", PRIMARY_PSM)
