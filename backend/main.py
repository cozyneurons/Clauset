"""
main.py

FastAPI entry point for the Railway GCC Contract Analyzer backend.

Phase 1 endpoint:
  POST /api/analyze
    - Accepts a PDF upload
    - Extracts text (PyMuPDF + OCR fallback)
    - Splits into 3 parts and sends to Gemini for clause mapping
    - Runs fuzzy fallback for missing candidates
    - Returns structured JSON analysis result

Run locally:
  uvicorn main:app --reload --port 8000
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from core.pdf_extractor import extract_pages, pages_to_full_text, split_pages_into_parts
from core.gemini_mapper import map_contract_to_gcc, MappingResult
from core.clause_matcher import extract_verbatim_text, fuzzy_search_missing

load_dotenv()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── GCC reference data path ──
GCC_CLAUSES_PATH = Path(__file__).parent / "data" / "gcc_clauses.json"

# ── FastAPI app ──
app = FastAPI(
    title="Railway GCC Contract Analyzer API",
    description="Analyzes Railway contract PDFs against the standard GCC clause library using Gemini.",
    version="1.0.0",
)

# ── CORS — allow React frontend (localhost:3000 for dev, Vercel domain for prod) ──
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Startup: load GCC clauses into memory
# ─────────────────────────────────────────────────────────────────────────────

GCC_CLAUSES: List[Dict[str, Any]] = []


@app.on_event("startup")
async def load_gcc_clauses() -> None:
    """Load gcc_clauses.json into memory at startup."""
    global GCC_CLAUSES
    if not GCC_CLAUSES_PATH.exists():
        logger.warning(
            "gcc_clauses.json not found at %s. "
            "Run: python scripts/extract_gcc_clauses.py to generate it.",
            GCC_CLAUSES_PATH,
        )
        GCC_CLAUSES = []
        return
    with open(GCC_CLAUSES_PATH, "r", encoding="utf-8") as f:
        GCC_CLAUSES = json.load(f)
    logger.info("Loaded %d GCC clauses from %s.", len(GCC_CLAUSES), GCC_CLAUSES_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health() -> Dict[str, Any]:
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "gcc_clauses_loaded": len(GCC_CLAUSES),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Contract Analysis Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze_contract(pdf: UploadFile = File(...)) -> JSONResponse:
    """
    Analyze an uploaded Railway contract PDF against the standard GCC clause library.

    Pipeline:
      1. Validate and save the uploaded PDF to a temp file.
      2. Extract text page-by-page (PyMuPDF + OCR fallback).
      3. Split pages into 3 parts.
      4. Send each part to Gemini for clause mapping (3 API calls total).
      5. Merge mapping results.
      6. Extract verbatim clause text using page-scoped fuzzy anchor matching.
      7. Run fuzzy keyword fallback for "missing" candidates.
      8. Return structured JSON result.

    Returns:
        JSON with keys:
          - filename: str
          - page_count: int
          - total_gcc_clauses: int
          - found_count: int
          - missing_count: int
          - part_errors: list[int]
          - clauses: list of {
                clause_id, clause_title, risk_category,
                status, page_number, confidence,
                verbatim_text, matched_keywords
            }
    """
    # ── Validate file type ──
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if not GCC_CLAUSES:
        raise HTTPException(
            status_code=503,
            detail=(
                "GCC clause library is not loaded. "
                "Run: python scripts/extract_gcc_clauses.py to generate gcc_clauses.json."
            ),
        )

    # ── Save upload to a temp file ──
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await pdf.read()
        tmp.write(content)
        tmp_path = tmp.name

    logger.info("Received PDF: %s (%d bytes). Temp path: %s", pdf.filename, len(content), tmp_path)

    try:
        # ── Step 1: Extract pages ──
        try:
            pages = extract_pages(tmp_path)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        page_count = len(pages)
        full_text = pages_to_full_text(pages)
        logger.info("Extracted %d pages, %d total chars.", page_count, len(full_text))

        # ── Step 2: Split into 3 parts ──
        parts = split_pages_into_parts(pages, n_parts=3)

        # ── Step 3–4: Run Gemini mapping ──
        mapping: MappingResult = map_contract_to_gcc(parts, GCC_CLAUSES)

        # ── Step 5: Extract verbatim text for found clauses ──
        gcc_lookup: Dict[str, Dict[str, Any]] = {c["clause_id"]: c for c in GCC_CLAUSES}
        clause_results: List[Dict[str, Any]] = []

        for cid, mapped in mapping.found.items():
            verbatim = extract_verbatim_text(mapped, pages)
            gcc_meta = gcc_lookup.get(cid, {})
            clause_results.append({
                "clause_id": cid,
                "clause_title": gcc_meta.get("clause_title", ""),
                "risk_category": gcc_meta.get("risk_category", "MEDIUM"),
                "section": gcc_meta.get("section", ""),
                "status": "present",
                "page_number": mapped.page_number,
                "confidence": mapped.confidence,
                "verbatim_text": verbatim or "",
                "matched_keywords": [],
            })

        # ── Step 6: Fuzzy fallback for missing candidates ──
        fuzzy_results = fuzzy_search_missing(
            missing_ids=mapping.missing_candidates,
            gcc_clauses=GCC_CLAUSES,
            full_text=full_text,
        )

        for cid, fuzzy_data in fuzzy_results.items():
            gcc_meta = gcc_lookup.get(cid, {})
            clause_results.append({
                "clause_id": cid,
                "clause_title": gcc_meta.get("clause_title", ""),
                "risk_category": gcc_meta.get("risk_category", "MEDIUM"),
                "section": gcc_meta.get("section", ""),
                "status": fuzzy_data["status"],   # "present_fuzzy" or "truly_missing"
                "page_number": None,
                "confidence": "low" if fuzzy_data["status"] == "present_fuzzy" else None,
                "verbatim_text": fuzzy_data.get("context") or "",
                "matched_keywords": fuzzy_data.get("matched_keywords", []),
            })

        # ── Sort: present first, then present_fuzzy, then truly_missing ──
        status_order = {"present": 0, "present_fuzzy": 1, "truly_missing": 2}
        clause_results.sort(key=lambda x: (status_order.get(x["status"], 3), x["clause_id"]))

        found_count = sum(1 for c in clause_results if c["status"] in ("present", "present_fuzzy"))
        missing_count = sum(1 for c in clause_results if c["status"] == "truly_missing")

        return JSONResponse(content={
            "filename": pdf.filename,
            "page_count": page_count,
            "total_gcc_clauses": len(GCC_CLAUSES),
            "found_count": found_count,
            "missing_count": missing_count,
            "part_errors": mapping.part_errors,
            "clauses": clause_results,
        })

    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
