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


class TestDebugFolderPruning:
    """debug_mode keeps the most recent folders instead of wiping other requests' output."""

    def test_keeps_recent_folders_and_the_current_one(self, tmp_path, monkeypatch):
        import os
        monkeypatch.setattr(tesseract_ocr, "DEBUG_FOLDER", str(tmp_path))

        for i in range(15):
            folder = tmp_path / f"old-{i:02d}"
            folder.mkdir()
            os.utime(folder, (1_000_000 + i, 1_000_000 + i))
        current = tmp_path / "current-request"
        current.mkdir()
        os.utime(current, (1, 1))  # oldest on disk, but it belongs to the running request

        TesseractOcr()._prune_debug_folders(keep="current-request")

        remaining = sorted(p.name for p in tmp_path.iterdir())
        assert "current-request" in remaining
        assert len(remaining) == tesseract_ocr.DEBUG_KEEP
        assert "old-14" in remaining and "old-00" not in remaining


class TestCropToContent:
    """Pages are cropped to their content and keep their colors (no grayscale)."""

    def test_card_on_white_page_is_cropped_in_color(self):
        page = Image.new("RGB", (1000, 1200), color=(255, 255, 255))
        page.paste((30, 90, 160), (200, 300, 500, 450))  # a colored "card"

        cropped = TesseractOcr()._crop_to_content(page)

        padding = tesseract_ocr.CROP_PADDING
        assert cropped.size == (300 + 2 * padding, 150 + 2 * padding)
        assert cropped.mode == "RGB"

    def test_blank_page_is_returned_untouched(self):
        page = Image.new("RGB", (400, 400), color=(255, 255, 255))

        assert TesseractOcr()._crop_to_content(page) is page
