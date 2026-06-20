import fitz  # PyMuPDF

from datetime import datetime

from app.exceptions.app_exception import AppException
from app.processors.base.base_processor import BaseProcessor
from app.helpers.logger import Logger


class PdfProcessor(BaseProcessor):
    """PDF document processor using PyMuPDF."""

    def process(self, file_path: str, from_page: int = None, to_page: int = None) -> dict:
        """
        Process a PDF file and return structured data.

        Args:
            file_path (str): Absolute path to the PDF file.
            from_page (int, optional): Start page (1-indexed).
            to_page (int, optional): End page (1-indexed).

        Returns:
            dict: Structured processing result.

        Raises:
            RuntimeError: If the file cannot be opened or processed.
            AppException: If page range exceeds document page count.
        """
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            Logger.error("Failed to open PDF file", file=file_path, detail=str(e))
            raise RuntimeError(f"Could not open file as PDF: {str(e)}") from e

        total_pages = len(doc)

        # Resolve and validate page range
        start, end = self._resolve_page_range(from_page, to_page, total_pages)

        metadata = self._extract_metadata(doc)
        pages_analysis = self._analyze_pages(doc, start, end)
        extracted_text = self._extract_text(doc, start, end)
        has_text = bool(extracted_text.strip())
        doc.close()

        diagnosis = self._build_diagnosis(has_text, pages_analysis)

        OCR_REASONS = {"low_text_density", "partial_text_extraction", "scanned_image_pdf", 
                    "text_rendered_as_paths", "corrupt_or_proprietary_encoding"}

        processing_method = "ocr_required" if diagnosis["reason"] in OCR_REASONS else "text_extraction"

        Logger.info(
            "PDF processed",
            pages=f"{start + 1}-{end}",
            chars=len(extracted_text.strip()),
            method=processing_method,
            diagnosis=diagnosis["reason"],
            confidence=diagnosis["confidence"],
        )

        return {
            "fileType": "pdf",
            "pages": total_pages,
            "processedPages": {"from": start + 1, "to": end},
            "hasText": has_text,
            "isScanned": not has_text,
            "processingMethod": processing_method,
            "text": extracted_text.strip() if has_text else None,
            "extractedFields": None,
            "metadata": metadata,
            "pagesAnalysis": pages_analysis,
            "diagnosis": diagnosis,
        }

    def _resolve_page_range(self, from_page: int | None, to_page: int | None, total_pages: int) -> tuple[int, int]:
        """
        Resolve and validate page range against total pages.

        Args:
            from_page (int | None): Requested start page (1-indexed).
            to_page (int | None): Requested end page (1-indexed).
            total_pages (int): Total pages in the document.

        Returns:
            tuple[int, int]: Zero-indexed start and end (exclusive) for fitz.

        Raises:
            AppException: If requested range exceeds document pages.
        """
        start = (from_page - 1) if from_page else 0
        end = to_page if to_page else total_pages

        if start >= total_pages:
            raise AppException(
                message=f"from_page ({from_page}) exceeds document total pages ({total_pages}).",
                status_code=422,
            )

        if end > total_pages:
            raise AppException(
                message=f"to_page ({to_page}) exceeds document total pages ({total_pages}).",
                status_code=422,
            )

        return start, end

    def _extract_text(self, doc: fitz.Document, start: int, end: int) -> str:
        """
        Extract embedded text from page range.

        Args:
            doc (fitz.Document): Opened PDF document.
            start (int): Zero-indexed start page.
            end (int): Zero-indexed end page (exclusive).

        Returns:
            str: Concatenated text from selected pages.
        """
        return "".join(doc[i].get_text() for i in range(start, end))

    def _parse_pdf_date(self, raw: str) -> str | None:
        """
        Convert PDF date string to ISO 8601 format.

        Args:
            raw (str): Raw PDF date e.g. D:20230105190725-06'00'

        Returns:
            str | None: ISO 8601 date string or None if unparseable.
        """
        if not raw or not raw.startswith("D:"):
            return None
        try:
            raw = raw[2:]
            dt = datetime.strptime(raw[:14], "%Y%m%d%H%M%S")
            return dt.isoformat()
        except ValueError:
            return None

    def _extract_metadata(self, doc: fitz.Document) -> dict:
        """
        Extract PDF document metadata.

        Args:
            doc (fitz.Document): Opened PDF document.

        Returns:
            dict: Document metadata including creator, producer and dates.
        """
        raw = doc.metadata or {}
        return {
            "title": raw.get("title") or None,
            "author": raw.get("author") or None,
            "creator": raw.get("creator") or None,
            "producer": raw.get("producer") or None,
            "creationDate": self._parse_pdf_date(raw.get("creationDate")),
            "modDate": self._parse_pdf_date(raw.get("modDate")),
        }

    def _analyze_pages(self, doc: fitz.Document, start: int, end: int) -> list[dict]:
        """
        Analyze pages within range: text blocks, images, fonts and character count.

        Args:
            doc (fitz.Document): Opened PDF document.
            start (int): Zero-indexed start page.
            end (int): Zero-indexed end page (exclusive).

        Returns:
            list[dict]: Per-page diagnostic information.
        """
        analysis = []

        for i in range(start, end):
            page = doc[i]
            text = page.get_text()
            raw_dict = page.get_text("rawdict")
            blocks = raw_dict.get("blocks", [])
            fonts = page.get_fonts(full=False)
            images = page.get_images(full=False)

            text_blocks = [b for b in blocks if b.get("type") == 0]
            image_blocks = [b for b in blocks if b.get("type") == 1]

            analysis.append({
                "page": i + 1,
                "charCount": len(text.strip()),
                "textBlocksDetected": len(text_blocks),
                "imageBlocksDetected": len(image_blocks),
                "embeddedImages": len(images),
                "embeddedFonts": len(fonts),
                "hasText": bool(text.strip()),
            })

        return analysis

    def _build_diagnosis(self, has_text: bool, pages_analysis: list[dict]) -> dict:
        """
        Build a diagnostic summary with scoring based on multiple signals.

        Args:
            has_text (bool): Whether any text was extracted.
            pages_analysis (list[dict]): Per-page analysis data.

        Returns:
            dict: Diagnosis with reason, confidence, signals and score.
        """
        total_pages = len(pages_analysis)
        total_chars = sum(p["charCount"] for p in pages_analysis)
        total_fonts = sum(p["embeddedFonts"] for p in pages_analysis)
        total_images = sum(p["embeddedImages"] for p in pages_analysis)
        total_image_blocks = sum(p["imageBlocksDetected"] for p in pages_analysis)
        total_text_blocks = sum(p["textBlocksDetected"] for p in pages_analysis)
        pages_with_text = sum(1 for p in pages_analysis if p["hasText"])

        ratio_text_pages = pages_with_text / total_pages if total_pages > 0 else 0
        avg_chars_per_page = total_chars / total_pages if total_pages > 0 else 0
        ratio_text_vs_image = total_chars / (total_image_blocks + 1)

        signals = {
            "totalChars": total_chars,
            "totalFonts": total_fonts,
            "totalImages": total_images,
            "totalImageBlocks": total_image_blocks,
            "totalTextBlocks": total_text_blocks,
            "pagesWithText": pages_with_text,
            "totalPages": total_pages,
            "ratioTextPages": round(ratio_text_pages, 2),
            "avgCharsPerPage": round(avg_chars_per_page, 2),
            "ratioTextVsImage": round(ratio_text_vs_image, 4),
        }

        # Low text density — has_text=True but content is insignificant vs images
        if has_text and avg_chars_per_page < 50 and total_image_blocks > 100:
            return {
                "reason": "low_text_density",
                "detail": "Text was detected but is insignificant compared to image content. OCR recommended.",
                "confidence": "high",
                "signals": signals,
            }

        # Partial extraction — some pages have text, others don't
        if has_text and ratio_text_pages < 0.5:
            return {
                "reason": "partial_text_extraction",
                "detail": "Only some pages contain extractable text. Document may be partially scanned.",
                "confidence": "medium",
                "signals": signals,
            }

        if has_text:
            return {
                "reason": "embedded_text_found",
                "detail": "Text was successfully extracted from the PDF.",
                "confidence": "high",
                "signals": signals,
            }

        # No text — evaluate why
        if total_images > 0 and total_fonts == 0:
            return {
                "reason": "scanned_image_pdf",
                "detail": "Pages contain images with no embedded fonts. Likely a scanned document.",
                "confidence": "high",
                "signals": signals,
            }

        if total_fonts > 0 and total_text_blocks > 0:
            return {
                "reason": "text_rendered_as_paths",
                "detail": "Fonts and text blocks detected but no readable text extracted. Text may be rendered as vectors/paths.",
                "confidence": "medium",
                "signals": signals,
            }

        if total_fonts > 0 and total_text_blocks == 0:
            return {
                "reason": "corrupt_or_proprietary_encoding",
                "detail": "Fonts are embedded but no text blocks found. Possible proprietary encoding or corrupt structure.",
                "confidence": "medium",
                "signals": signals,
            }

        return {
            "reason": "unknown",
            "detail": "Could not determine why text extraction failed.",
            "confidence": "low",
            "signals": signals,
        }