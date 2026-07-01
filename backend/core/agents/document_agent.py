"""
core/agents/document_agent.py

Agent 1 — Document Parser Agent
Wraps PyMuPDF + OCR extraction logic from pdf_extractor.py.
"""

from typing import Any, Callable, Dict, List, Optional

from core.agents.base_agent import BaseAgent, AgentEvent
from core.pdf_extractor import extract_pages, is_valid_pdf, pages_to_full_text, split_pages_into_parts


class DocumentAgent(BaseAgent):
    """
    Parses an uploaded PDF file and returns structured page data.

    Input:  {"pdf_path": str}
    Output: {
        "pages": List[Dict],
        "full_text": str,
        "parts": List[List[Dict]],  # 3 parts for Gemini
        "page_count": int,
    }
    """

    name = "DocumentParser"

    def run(
        self,
        input_data: Dict[str, Any],
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Dict[str, Any]:
        pdf_path = input_data["pdf_path"]

        self._emit(emit, "started", 0, "Validating PDF file...")

        if not is_valid_pdf(pdf_path):
            raise ValueError(f"File is not a valid PDF: {pdf_path}")

        self._emit(emit, "running", 10, "Extracting text from PDF pages...")

        pages = extract_pages(pdf_path)
        page_count = len(pages)

        self._emit(emit, "running", 60, f"Extracted {page_count} pages. Splitting into 3 parts...")

        full_text = pages_to_full_text(pages)
        parts = split_pages_into_parts(pages, n_parts=3)

        self._emit(emit, "complete", 100, f"Document parsed: {page_count} pages, split into 3 parts.", {
            "page_count": page_count,
            "total_chars": len(full_text),
            "part_sizes": [len(p) for p in parts],
        })

        return {
            "pages": pages,
            "full_text": full_text,
            "parts": parts,
            "page_count": page_count,
        }
