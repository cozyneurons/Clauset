"""
core/pdf_extractor.py

PDF text extraction for the Railway GCC Contract Analyzer.
Uses PyMuPDF for digital PDFs with pytesseract as OCR fallback for scanned pages.
Returns per-page text data for use by the 3-part Gemini mapping pipeline.
"""

import io
import logging
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"


def _is_scanned_or_garbled(text: str) -> bool:
    """Return True if page text appears to be scanned/garbled (too short or too few alpha chars)."""
    stripped = text.strip()
    if len(stripped) < 50:
        return True
    alpha = sum(1 for c in stripped if c.isalpha())
    ratio = alpha / len(stripped)
    if ratio < 0.30:
        logger.debug("Garbled text detected (%.1f%% alphabetic).", ratio * 100)
        return True
    return False


def _ocr_page(page: fitz.Page) -> str:
    """Rasterise page at 300 DPI and extract text with Tesseract OCR."""
    try:
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        with io.BytesIO(img_bytes) as buf:
            pil_image = Image.open(buf).convert("RGB")
            pil_image.load()
        return pytesseract.image_to_string(pil_image, lang="eng", config="--psm 6")
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return ""


def is_valid_pdf(path: str) -> bool:
    """Check the PDF magic bytes to validate the uploaded file."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == PDF_MAGIC
    except OSError:
        return False


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from each page of a PDF.

    Returns:
        A list of dicts: [{"page_num": int, "text": str, "method": str}, ...]
        - method is "digital" or "ocr"

    Raises:
        RuntimeError: if the file cannot be opened.
    """
    if not is_valid_pdf(pdf_path):
        raise ValueError(f"File does not appear to be a valid PDF: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF with PyMuPDF: {exc}") from exc

    total = len(doc)
    logger.info("PDF opened: %d pages.", total)

    pages: List[Dict[str, Any]] = []

    for i in range(total):
        page = doc[i]
        raw = page.get_text("text")

        if _is_scanned_or_garbled(raw):
            logger.info("Page %d/%d: OCR fallback.", i + 1, total)
            text = _ocr_page(page)
            method = "ocr"
        else:
            text = raw
            method = "digital"

        pages.append({
            "page_num": i + 1,
            "text": text,
            "method": method,
            "char_count": len(text),
        })

    doc.close()
    ocr_count = sum(1 for p in pages if p["method"] == "ocr")
    logger.info(
        "Extraction complete: %d digital, %d OCR pages.",
        total - ocr_count,
        ocr_count,
    )
    return pages


def pages_to_full_text(pages: List[Dict[str, Any]]) -> str:
    """Join per-page text into a single string separated by form-feeds."""
    return "\f".join(p["text"] for p in pages)


def split_pages_into_parts(
    pages: List[Dict[str, Any]],
    n_parts: int = 3,
) -> List[List[Dict[str, Any]]]:
    """
    Divide the page list into n_parts roughly equal groups.

    Args:
        pages:   The full list of per-page dicts from extract_pages().
        n_parts: Number of parts to split into (default 3 for 3 Gemini requests).

    Returns:
        A list of n_parts sub-lists of page dicts.
    """
    total = len(pages)
    if total == 0:
        return [[] for _ in range(n_parts)]

    chunk_size = max(1, -(-total // n_parts))  # ceiling division
    parts = []
    for i in range(n_parts):
        start = i * chunk_size
        end = min(start + chunk_size, total)
        if start < total:
            parts.append(pages[start:end])
        else:
            parts.append([])

    logger.info(
        "Split %d pages into %d parts: sizes %s",
        total,
        n_parts,
        [len(p) for p in parts],
    )
    return parts
