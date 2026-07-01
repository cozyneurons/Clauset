"""
main.py

FastAPI entry point for the Railway GCC Contract Analyzer backend.

Phase 1 endpoint:
  POST /api/analyze
    - Accepts a PDF upload
    - Extracts text (PyMuPDF + OCR fallback)
    - Splits into 3 parts and sends to Gemini for clause mapping
    - Runs fuzzy fallback for missing candidates
    - Runs optional Gemini batch validation when enabled
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

from core.agents.pipeline import ContractAnalysisPipeline

load_dotenv()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _has_real_env_key(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and not value.startswith("your_"))

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
        "gemini_validation_enabled": os.getenv("GEMINI_VALIDATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"},
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        "gemini_api_key_configured": _has_real_env_key("GEMINI_API_KEY"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Contract Analysis Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/gcc-clauses")
async def get_gcc_clauses(
    risk: str = None,
    search: str = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Browse all extracted GCC clauses.

    Query params:
      - risk: Filter by risk_category (HIGH, MEDIUM, LOW)
      - search: Keyword search in clause_id, clause_title, clause_text
      - limit: Number of results to return (default 50)
      - offset: Pagination offset (default 0)
    """
    clauses = GCC_CLAUSES

    if risk:
        clauses = [c for c in clauses if c.get("risk_category", "").upper() == risk.upper()]

    if search:
        q = search.lower()
        clauses = [
            c for c in clauses
            if q in c.get("clause_id", "").lower()
            or q in c.get("clause_title", "").lower()
            or q in c.get("clause_text", "").lower()
            or any(q in kw.lower() for kw in c.get("keywords", []))
        ]

    total = len(clauses)
    paginated = clauses[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "clauses": paginated,
    }


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
      8. Run Gemini second-pass validation batch by batch, when configured.
      9. Return structured JSON result.

    Returns:
        JSON with keys:
          - filename: str
          - page_count: int
          - total_gcc_clauses: int
          - found_count: int
          - missing_count: int
          - part_errors: list[int]
          - gemini_summary: dict
          - clauses: list of {
                clause_id, clause_title, risk_category,
                status, final_status, page_number, confidence,
                gemini_status, gemini_confidence, gemini_reason,
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
        pipeline = ContractAnalysisPipeline()
        try:
            result = pipeline.run({
                "pdf_path": tmp_path,
                "filename": pdf.filename,
                "gcc_clauses": GCC_CLAUSES,
            })
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return JSONResponse(content=result)

    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
