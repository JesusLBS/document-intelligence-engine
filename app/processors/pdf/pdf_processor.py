import fitz  # PyMuPDF

from app.processors.base.base_processor import BaseProcessor
from datetime import datetime

class PdfProcessor(BaseProcessor):
    """PDF document processor using PyMuPDF."""

    def process(self, file_path: str) -> dict:
        """
        Process a PDF file and return structured data.

        Args:
            file_path (str): Absolute path to the PDF file.

        Returns:
            dict: Structured processing result.

        """
        doc = fitz.open(file_path)
        pages = len(doc)
        metadata = self._extract_metadata(doc)
        pages_analysis = self._analyze_pages(doc)
        extracted_text = self._extract_text(doc)
        has_text = bool(extracted_text.strip())
        doc.close()

        diagnosis = self._build_diagnosis(has_text, pages_analysis)

        return {
            "fileType": "pdf",
            "pages": pages,
            "hasText": has_text,
            "isScanned": not has_text,
            "processingMethod": "text_extraction" if has_text else "ocr_required",
            "text": extracted_text.strip() if has_text else None,
            "extractedFields": None,
            "metadata": metadata,
            "pagesAnalysis": pages_analysis,
            "diagnosis": diagnosis,
        }

    def _extract_text(self, doc: fitz.Document) -> str:
        """
        Extract embedded text from all pages.

        Args:
            doc (fitz.Document): Opened PDF document.

        Returns:
            str: Concatenated text from all pages.
        """
        return "".join(page.get_text() for page in doc)

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
            raw = raw[2:]  # strip D:
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

    def _analyze_pages(self, doc: fitz.Document) -> list[dict]:
        """
        Analyze each page: text blocks, images, fonts and character count.

        Args:
            doc (fitz.Document): Opened PDF document.

        Returns:
            list[dict]: Per-page diagnostic information.
        """
        analysis = []

        for i, page in enumerate(doc):
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
        Build a diagnostic summary explaining why text extraction succeeded or failed.

        Args:
            has_text (bool): Whether any text was extracted.
            pages_analysis (list[dict]): Per-page analysis data.

        Returns:
            dict: Diagnosis with probable cause and confidence level.
        """
        if has_text:
            return {
                "reason": "embedded_text_found",
                "detail": "Text was successfully extracted from the PDF.",
                "confidence": "high",
            }

        total_fonts = sum(p["embeddedFonts"] for p in pages_analysis)
        total_images = sum(p["embeddedImages"] for p in pages_analysis)
        total_text_blocks = sum(p["textBlocksDetected"] for p in pages_analysis)

        if total_images > 0 and total_fonts == 0:
            return {
                "reason": "scanned_image_pdf",
                "detail": "Pages contain images with no embedded fonts. Likely a scanned document.",
                "confidence": "high",
            }

        if total_fonts > 0 and total_text_blocks > 0:
            return {
                "reason": "text_rendered_as_paths",
                "detail": "Fonts and text blocks detected but no readable text extracted. Text may be rendered as vectors/paths.",
                "confidence": "medium",
            }

        if total_fonts > 0 and total_text_blocks == 0:
            return {
                "reason": "corrupt_or_proprietary_encoding",
                "detail": "Fonts are embedded but no text blocks found. Possible proprietary encoding or corrupt structure.",
                "confidence": "medium",
            }

        return {
            "reason": "unknown",
            "detail": "Could not determine why text extraction failed.",
            "confidence": "low",
        }