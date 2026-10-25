from PIL import Image

from app.processors.pdf import page_renderer
from app.processors.pdf.page_renderer import CROP_PADDING, crop_to_content, render_pdf_pages


class TestCropToContent:
    """Pages are cropped to their content and keep their colors (no grayscale)."""

    def test_card_on_white_page_is_cropped_in_color(self):
        page = Image.new("RGB", (1000, 1200), color=(255, 255, 255))
        page.paste((30, 90, 160), (200, 300, 500, 450))  # a colored "card"

        cropped = crop_to_content(page)

        assert cropped.size == (300 + 2 * CROP_PADDING, 150 + 2 * CROP_PADDING)
        assert cropped.mode == "RGB"

    def test_blank_page_is_returned_untouched(self):
        page = Image.new("RGB", (400, 400), color=(255, 255, 255))

        assert crop_to_content(page) is page


class TestRenderRange:
    """Only the requested pages are rendered."""

    def test_page_range_is_passed_to_the_renderer(self, monkeypatch):
        calls = []

        def convert_from_path(path, first_page=None, last_page=None, dpi=None):
            calls.append((first_page, last_page, dpi))
            return [Image.new("RGB", (50, 50), color=(255, 255, 255))]

        monkeypatch.setattr(page_renderer, "convert_from_path", convert_from_path)

        pages = render_pdf_pages("doc.pdf", from_page=2, to_page=2)

        assert calls == [(2, 2, page_renderer.RENDER_DPI)]
        assert len(pages) == 1
