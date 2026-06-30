"""
core/ocr_engine.py

PDF text extraction module for the Railway GCC Contract Risk Analyzer.
Uses PyMuPDF as the primary extraction method and pytesseract as OCR fallback
for scanned or image-based pages. Implements a two-stage chunking strategy:
    Stage 1 — Smart header-based chunking (preferred for structured contracts)
    Stage 2 — Word-count fallback chunking (for unstructured documents)
"""

import re
import io
import logging
from typing import List, Dict, Any

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extracts text from PDF files using PyMuPDF for digital PDFs and
    pytesseract for scanned or image-based pages.

    Implements the two-stage chunking strategy described in the project spec.
    """

    # Regex pattern to detect Railway contract section headers.
    # Detects: "Clause 47", "CLAUSE 47", "47.", "47.1", "47.1.2",
    #          "Section 12", "SECTION 12", "Article 5", "ARTICLE 5"
    HEADER_PATTERN = re.compile(
        r"""
        (?:^|\n)                          # Start of line or newline
        (?:
            (?:Clause|CLAUSE|Section|SECTION|Article|ARTICLE)  # Keyword
            \s+\d{1,3}(?:\.\d{1,3})*     # Followed by number like "47" or "47.1.2"
            |
            \d{1,3}\.\d{1,3}(?:\.\d{1,3})*  # Standalone "47.1" or "47.1.2"
            |
            \d{1,3}\.                         # Standalone "47."
        )
        (?:\s|$)                          # Followed by whitespace or end of string
        """,
        re.VERBOSE | re.MULTILINE,
    )

    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF file, using OCR as a fallback for scanned pages.

        For each page:
          - Attempts digital extraction via PyMuPDF.
          - If the extracted text has fewer than 50 characters OR fewer than
            30% alphabetic characters (garbled text detection), the page is
            treated as a scanned page and re-processed with pytesseract at 300 DPI.

        Args:
            pdf_path: Absolute path to the PDF file to extract.

        Returns:
            A dict with keys:
              "full_text"   : str — all pages joined with form-feed separator
              "page_count"  : int — number of pages in the PDF
              "method_used" : str — "digital", "ocr", or "mixed"
              "pages"       : list[dict] — per-page breakdown with text and method
        """
        pages_data: List[Dict[str, Any]] = []
        digital_count = 0
        ocr_count = 0

        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            logger.error("Failed to open PDF with PyMuPDF: %s", exc)
            raise

        total_pages = len(doc)
        logger.info("PDF opened: %d pages", total_pages)

        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                raw_text = page.get_text("text")  # type: ignore[attr-defined]

                if self._is_scanned_or_garbled(raw_text):
                    # Rasterize page at 300 DPI and run OCR
                    logger.info("Page %d classified as scanned/garbled — running OCR.", page_num + 1)
                    ocr_text = self._ocr_page(page)
                    pages_data.append({
                        "page_num": page_num + 1,
                        "text": ocr_text,
                        "method": "ocr",
                        "char_count": len(ocr_text),
                    })
                    ocr_count += 1
                else:
                    pages_data.append({
                        "page_num": page_num + 1,
                        "text": raw_text,
                        "method": "digital",
                        "char_count": len(raw_text),
                    })
                    digital_count += 1

            except Exception as exc:
                logger.error("Failed to process page %d: %s — skipping.", page_num + 1, exc)
                pages_data.append({
                    "page_num": page_num + 1,
                    "text": "",
                    "method": "error",
                    "char_count": 0,
                })

        doc.close()

        full_text = "\f".join(p["text"] for p in pages_data)

        if ocr_count == 0:
            method_used = "digital"
        elif digital_count == 0:
            method_used = "ocr"
        else:
            method_used = "mixed"

        logger.info(
            "Extraction complete: %d digital pages, %d OCR pages. Method: %s",
            digital_count,
            ocr_count,
            method_used,
        )

        return {
            "full_text": full_text,
            "page_count": total_pages,
            "method_used": method_used,
            "pages": pages_data,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_scanned_or_garbled(self, text: str) -> bool:
        """
        Determine whether a page's extracted text indicates a scanned or garbled page.

        Criteria:
          - Fewer than 50 characters total, OR
          - Fewer than 30% of the characters are alphabetic (garbled/symbol-heavy text).

        Args:
            text: Raw text extracted by PyMuPDF from a single page.

        Returns:
            True if the page should be treated as scanned/garbled.
        """
        stripped = text.strip()
        if len(stripped) < 50:
            return True

        alpha_count = sum(1 for c in stripped if c.isalpha())
        alpha_ratio = alpha_count / len(stripped) if stripped else 0.0
        if alpha_ratio < 0.30:
            logger.debug(
                "Garbled text detected (%.1f%% alphabetic). Treating as scanned.",
                alpha_ratio * 100,
            )
            return True

        return False

    def _ocr_page(self, page: fitz.Page) -> str:
        """
        Rasterize a PyMuPDF page at 300 DPI and extract text using pytesseract.

        Args:
            page: A PyMuPDF page object.

        Returns:
            OCR-extracted text string. Returns empty string on failure.
        """
        try:
            # 300 DPI matrix: scale factor = 300/72 ≈ 4.167
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)  # type: ignore[attr-defined]

            # Convert pixmap bytes to PIL Image
            img_data = pix.tobytes("png")
            with io.BytesIO(img_data) as buf:
                pil_image = Image.open(buf).convert("RGB")
                pil_image.load()  # force decode before buffer closes

            # Run tesseract with English and Hindi languages (common in Indian contracts)
            ocr_text: str = pytesseract.image_to_string(
                pil_image,
                lang="eng",
                config="--psm 6",  # Assume a single uniform block of text
            )
            return ocr_text
        except Exception as exc:
            logger.error("OCR failed on page: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Public chunking API
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        full_text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> List[str]:
        """
        Split a full contract text into processable chunks using a two-stage strategy.

        Stage 1 — Smart Header-Based Chunking (always attempted first):
            Scans full_text for Railway contract section headers (Clause N, Section N,
            Article N, N.N, N.N.N). If 5 or more headers are detected, the text is
            split at each header boundary. Each resulting segment is returned as one
            chunk, with the header prepended. Segments shorter than 80 words are
            discarded as boilerplate.

        Stage 2 — Fallback Word-Count Chunking (only if Stage 1 finds < 5 headers):
            Splits the text into overlapping windows of `chunk_size` words with
            `overlap` words shared between consecutive chunks.

        Args:
            full_text:  The full extracted text of the contract.
            chunk_size: Target chunk size in words for the word-count fallback.
            overlap:    Number of words to overlap between consecutive word-count chunks.

        Returns:
            List of text chunks ready for embedding and LLM analysis.
        """
        if not full_text or not full_text.strip():
            logger.warning("chunk_text called with empty text.")
            return []

        # Stage 1: header-based chunking
        header_chunks = self._header_based_chunks(full_text)
        if header_chunks is not None:
            return header_chunks

        # Stage 2: word-count fallback
        return self._word_count_chunks(full_text, chunk_size, overlap)

    def _header_based_chunks(self, full_text: str) -> List[str] | None:
        """
        Attempt header-based chunking of the contract text.

        Returns a list of clause-segment strings if 5 or more headers are found,
        otherwise returns None to signal that the fallback should be used.

        Args:
            full_text: The full extracted contract text.

        Returns:
            List of segment strings, or None if fewer than 5 headers were found.
        """
        matches = list(self.HEADER_PATTERN.finditer(full_text))

        if len(matches) < 5:
            logger.info(
                "Header-based chunking skipped: only %d headers found (need ≥ 5).",
                len(matches),
            )
            return None

        # Build segments by splitting at each header boundary
        segments: List[str] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            header_text = match.group(0).strip()
            segment_body = full_text[start:end].strip()

            # Prepend the header so the LLM always knows which clause it reads
            if header_text not in segment_body[: len(header_text) + 5]:
                segment = f"{header_text}\n{segment_body}"
            else:
                segment = segment_body

            # Discard very short segments (blank pages, page numbers, etc.)
            word_count = len(segment.split())
            if word_count < 80:
                logger.debug("Skipping short segment (%d words): %s...", word_count, segment[:40])
                continue

            segments.append(segment)

        logger.info("Header-based chunking: found %d clause segments.", len(segments))
        return segments

    def _word_count_chunks(
        self,
        full_text: str,
        chunk_size: int,
        overlap: int,
    ) -> List[str]:
        """
        Split text into overlapping word-count chunks.

        Args:
            full_text:  The text to split.
            chunk_size: Number of words per chunk.
            overlap:    Number of words shared between consecutive chunks.

        Returns:
            List of chunk strings.
        """
        words = full_text.split()
        if not words:
            return []

        chunks: List[str] = []
        step = max(1, chunk_size - overlap)
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))
            if end == len(words):
                break
            start += step

        logger.info("Fallback word-count chunking: produced %d chunks.", len(chunks))
        return chunks
