from pdf2image import convert_from_path
from PIL import Image

from app.helpers.logger import Logger


# Rendering and preprocessing, measured on samples/pdf/ine_sample.pdf (a color INE photo on a
# white letter page), scoring OCR text by card labels and ID patterns found, and by how many
# fields a text-only AI extracted from it (2026-10-25):
#   - full page, grayscale (old pipeline): 0-3 of 14 points; text-only AI got 0/7 fields
#   - cropped to the content area: 9-10 points; text-only AI got 5-6/7 fields matching Gemini
#   - grayscale vs color made no real difference (color slightly better); Tesseract binarizes itself
#   - 400 DPI beat 300 DPI (only variant reading the clave de elector) for +0.4 s per page
RENDER_DPI = 400
# Pixels darker than this count as content when looking for the area to crop.
CONTENT_THRESHOLD = 235
CROP_PADDING = 20


def render_pdf_pages(file_path: str, from_page: int = None, to_page: int = None) -> list[Image.Image]:
    """
    Render the requested PDF pages as color images cropped to their content.

    Used for OCR and for debug snapshots; only the requested range is rendered.

    Args:
        file_path (str): Path to the PDF file.
        from_page (int, optional): Start page (1-indexed). None means first page.
        to_page (int, optional): End page (1-indexed). None means last page.

    Returns:
        list[Image.Image]: One cropped image per page, in page order.
    """
    pages = convert_from_path(file_path, first_page=from_page, last_page=to_page, dpi=RENDER_DPI)
    Logger.info("PDF pages rendered", from_page=from_page, to_page=to_page, count=len(pages))
    return [crop_to_content(page) for page in pages]


def crop_to_content(image: Image.Image) -> Image.Image:
    """
    Crop the page to the area that actually has content, keeping the original colors.

    A photographed ID card on a mostly white page defeats Tesseract's layout analysis;
    cropping to the card fixes it. On full-page documents the crop only trims margins.
    No grayscale conversion: measured, it did not help (see RENDER_DPI notes).

    Args:
        image (Image.Image): Rendered page.

    Returns:
        Image.Image: Cropped page (the original image if the page is blank).
    """
    mask = image.convert("L").point(lambda pixel: 255 if pixel < CONTENT_THRESHOLD else 0)
    box = mask.getbbox()
    if not box:
        return image

    left, top, right, bottom = box
    return image.crop((
        max(left - CROP_PADDING, 0),
        max(top - CROP_PADDING, 0),
        min(right + CROP_PADDING, image.width),
        min(bottom + CROP_PADDING, image.height),
    ))
