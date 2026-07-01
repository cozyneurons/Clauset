"""
scripts/extract_gcc_clauses.py

One-time script to extract all Railway GCC clauses from the official GCC PDF
and store them in a clean, versioned JSON structure at data/gcc_clauses.json.

Usage:
    python scripts/extract_gcc_clauses.py --pdf path/to/gcc.pdf
    python scripts/extract_gcc_clauses.py --pdf path/to/gcc.pdf --output data/gcc_clauses.json

If no --pdf is provided, the script will generate data/gcc_clauses.json from
the built-in seed data (useful for bootstrapping without the official PDF).
"""

import os
import re
import io
import json
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ── Try importing optional dependencies (not available until pip install) ──
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Output directory (relative to this script's parent) ──
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT = BACKEND_DIR / "data" / "gcc_clauses.json"

# ── Gemini config ──
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — PDF Text Extraction
# ─────────────────────────────────────────────────────────────────────────────

def _is_scanned_or_garbled(text: str) -> bool:
    """Return True if the page text looks like a scanned/garbled page."""
    stripped = text.strip()
    if len(stripped) < 50:
        return True
    alpha = sum(1 for c in stripped if c.isalpha())
    return (alpha / len(stripped)) < 0.30


def _ocr_page(page) -> str:
    """Rasterise a PyMuPDF page at 300 DPI and run Tesseract OCR."""
    if not OCR_AVAILABLE:
        logger.warning("pytesseract / PIL not installed — skipping OCR fallback.")
        return ""
    try:
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        with io.BytesIO(img_data) as buf:
            pil_image = Image.open(buf).convert("RGB")
            pil_image.load()
        return pytesseract.image_to_string(pil_image, lang="eng", config="--psm 6")
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract full text from the GCC PDF using PyMuPDF with OCR fallback.
    Returns the concatenated text of all pages joined by form-feed characters.
    """
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed. Run: pip install PyMuPDF")

    logger.info("Opening PDF: %s", pdf_path)
    doc = fitz.open(pdf_path)
    pages_text: List[str] = []

    for i in range(len(doc)):
        page = doc[i]
        raw = page.get_text("text")
        if _is_scanned_or_garbled(raw):
            logger.info("Page %d: OCR fallback triggered.", i + 1)
            text = _ocr_page(page)
        else:
            text = raw
        pages_text.append(text)
        logger.info("Page %d/%d extracted (%d chars).", i + 1, len(doc), len(text))

    doc.close()
    full_text = "\f".join(pages_text)
    logger.info("Extraction complete. Total characters: %d", len(full_text))
    return full_text


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Gemini Extraction
# ─────────────────────────────────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """
You are a senior legal analyst specialising in Indian Railways General Conditions of Contract (GCC).
Your task is to extract every distinct clause from the GCC document text provided, and return them
as a JSON array. Follow these rules strictly:

1. Include ALL clauses, sub-clauses, and articles — do not omit any.
2. For each clause output EXACTLY these fields:
   - "clause_id": The official clause/section identifier (e.g. "GCC-1", "GCC-47.1", "Clause 14(2)").
     Infer from numbering in the text. Use "GCC-<number>" format where possible.
   - "clause_title": The official title or heading of the clause (short, ≤ 10 words).
   - "clause_text": The complete verbatim text of the clause body.
   - "risk_category": Your assessment — one of "HIGH", "MEDIUM", or "LOW" — based on contractor risk.
   - "section": The parent section/part name this clause belongs to (e.g. "Part I — General").
   - "keywords": An array of 5–10 key legal/contractual terms from this clause.
3. Return ONLY the JSON array — no markdown fences, no explanatory text, nothing else.
4. If a clause is split across a page break, reconstruct it as a single entry.
"""


def extract_clauses_with_gemini(full_text: str) -> List[Dict[str, Any]]:
    """
    Send the full GCC text to Gemini and get a structured clause list back.
    Handles large texts by chunking into ~80,000-character segments and merging.
    """
    if not GENAI_AVAILABLE:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in your .env file.")

    client = genai.Client(api_key=api_key)

    # Split into chunks of ~80k characters with 2k character overlap
    CHUNK_SIZE = 80_000
    OVERLAP = 2_000
    chunks: List[str] = []
    start = 0
    while start < len(full_text):
        end = min(start + CHUNK_SIZE, len(full_text))
        chunks.append(full_text[start:end])
        if end == len(full_text):
            break
        start += CHUNK_SIZE - OVERLAP

    logger.info("GCC text split into %d chunk(s) for Gemini extraction.", len(chunks))

    all_clauses: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for idx, chunk in enumerate(chunks):
        logger.info("Sending chunk %d/%d to Gemini (%d chars)...", idx + 1, len(chunks), len(chunk))
        prompt = (
            f"{EXTRACTION_SYSTEM_PROMPT}\n\n"
            f"--- GCC DOCUMENT TEXT (part {idx + 1} of {len(chunks)}) ---\n{chunk}"
        )
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            raw_json = response.text.strip()
            clauses = json.loads(raw_json)
            if not isinstance(clauses, list):
                logger.error("Gemini returned non-list JSON for chunk %d. Skipping.", idx + 1)
                continue
            for clause in clauses:
                cid = clause.get("clause_id", "")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    all_clauses.append(clause)
                    logger.debug("Extracted clause: %s", cid)
            logger.info("Chunk %d: extracted %d new clauses.", idx + 1, len(clauses))
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse JSON from Gemini for chunk %d: %s", idx + 1, exc)
        except Exception as exc:
            logger.error("Gemini API error on chunk %d: %s", idx + 1, exc)

    logger.info("Total unique clauses extracted: %d", len(all_clauses))
    return all_clauses


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Validation
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"clause_id", "clause_title", "clause_text", "risk_category", "section", "keywords"}
VALID_RISK_CATEGORIES = {"HIGH", "MEDIUM", "LOW"}


def validate_and_clean(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate each clause against the required schema.
    Drops invalid clauses and normalises risk categories.
    Returns the cleaned list.
    """
    clean: List[Dict[str, Any]] = []
    for i, clause in enumerate(clauses):
        missing = REQUIRED_FIELDS - set(clause.keys())
        if missing:
            logger.warning("Clause %d missing fields %s — skipping.", i, missing)
            continue
        # Normalise risk category
        clause["risk_category"] = clause["risk_category"].upper().strip()
        if clause["risk_category"] not in VALID_RISK_CATEGORIES:
            clause["risk_category"] = "MEDIUM"
        # Ensure keywords is a list
        if isinstance(clause["keywords"], str):
            clause["keywords"] = [k.strip() for k in clause["keywords"].split(",")]
        # Strip whitespace from text fields
        clause["clause_text"] = clause["clause_text"].strip()
        clause["clause_title"] = clause["clause_title"].strip()
        clean.append(clause)
    logger.info("Validation complete: %d/%d clauses passed.", len(clean), len(clauses))
    return clean


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Seed Data (fallback when no PDF is available)
# ─────────────────────────────────────────────────────────────────────────────

# A representative seed of well-known Railway GCC clauses.
# This is used when the script is run without a --pdf argument.
# Expand this list as needed before you have the official PDF.
GCC_SEED_CLAUSES: List[Dict[str, Any]] = [
    {
        "clause_id": "GCC-1",
        "clause_title": "Definitions",
        "clause_text": (
            "In this Contract, the following words and expressions shall have the meanings "
            "hereby assigned to them: 'Employer' means the Railway Administration; 'Contractor' "
            "means the person or firm whose tender has been accepted; 'Engineer' means the "
            "designated railway officer for administering the contract; 'Works' means the works "
            "to be executed in accordance with the Contract."
        ),
        "risk_category": "LOW",
        "section": "Part I — General Conditions",
        "keywords": ["definitions", "employer", "contractor", "engineer", "works"],
    },
    {
        "clause_id": "GCC-4",
        "clause_title": "Performance Security",
        "clause_text": (
            "The Contractor shall furnish to the Employer a Performance Security within 21 days "
            "of receipt of the Letter of Acceptance. The Performance Security shall be an "
            "unconditional bank guarantee from a scheduled commercial bank for 10% of the "
            "Contract Price, valid through the Defects Notification Period plus 60 days. "
            "Failure to submit the Performance Security entitles the Employer to terminate the Contract."
        ),
        "risk_category": "HIGH",
        "section": "Part I — General Conditions",
        "keywords": ["performance security", "bank guarantee", "10 percent", "termination", "letter of acceptance"],
    },
    {
        "clause_id": "GCC-8",
        "clause_title": "Commencement of Works",
        "clause_text": (
            "The Contractor shall commence the Works within 14 days of receiving the "
            "Engineer's Notice to Commence. The Contractor shall proceed with the Works with "
            "due expedition and without delay in accordance with the Contract."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["commencement", "notice to commence", "expedition", "delay"],
    },
    {
        "clause_id": "GCC-11",
        "clause_title": "Defects Liability Period",
        "clause_text": (
            "The Defects Notification Period shall be 12 months from the date of issue of the "
            "Taking Over Certificate. During the DNP, the Contractor shall rectify all defects "
            "at no additional cost to the Employer. The Performance Certificate is issued at "
            "the end of the DNP after all defects are rectified."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["defects", "DNP", "taking over certificate", "performance certificate", "rectification"],
    },
    {
        "clause_id": "GCC-13",
        "clause_title": "Variations",
        "clause_text": (
            "The Engineer may issue Variation Orders at any time before the Taking Over "
            "Certificate. Variations may include changes to quantities, quality, dimensions, "
            "or scope. Total Variations shall not exceed 25% of the Contract Price without "
            "competent authority approval. The Contractor shall not vary the Works without a "
            "written Variation Order."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["variation", "variation order", "scope change", "25 percent", "engineer"],
    },
    {
        "clause_id": "GCC-14",
        "clause_title": "Payment Terms",
        "clause_text": (
            "The Contractor shall submit monthly Interim Payment Applications to the Engineer. "
            "The Engineer shall certify within 28 days and the Employer shall pay within 28 days "
            "of certification. Retention of 5% is deducted from interim payments, released "
            "50% at Taking Over and 50% at Performance Certificate. Late payment attracts "
            "financing charges at the rate specified in the Contract Data."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["payment", "interim payment", "retention", "28 days", "financing charges"],
    },
    {
        "clause_id": "GCC-19",
        "clause_title": "Force Majeure",
        "clause_text": (
            "Force Majeure means an exceptional event beyond a Party's control that could not "
            "have been foreseen or avoided. This includes war, terrorism, natural disasters, "
            "and riots. The affected Party must notify within 14 days. Neither Party may "
            "terminate unless Force Majeure continues beyond 84 days. The Contractor is "
            "entitled to extension of time but not additional payment."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["force majeure", "beyond control", "notice", "84 days", "extension of time"],
    },
    {
        "clause_id": "GCC-20",
        "clause_title": "Dispute Resolution and Arbitration",
        "clause_text": (
            "Disputes shall first be referred to the Engineer for determination within 28 days. "
            "If dissatisfied, either Party may give notice and refer to arbitration under the "
            "Arbitration and Conciliation Act 1996. A sole arbitrator is mutually appointed "
            "or by Railway Authority. Seat of arbitration is New Delhi. The Contractor shall "
            "continue Works pending dispute resolution."
        ),
        "risk_category": "MEDIUM",
        "section": "Part I — General Conditions",
        "keywords": ["dispute", "arbitration", "engineer determination", "Arbitration Act", "New Delhi"],
    },
    {
        "clause_id": "GCC-47",
        "clause_title": "Termination by Employer",
        "clause_text": (
            "The Employer may terminate the Contract after a 28-day cure period notice if the "
            "Contractor abandons the Works, fails to proceed, subcontracts without consent, or "
            "becomes insolvent. Upon termination, the Employer may forfeit the Performance "
            "Security and recover all losses from an alternate contractor."
        ),
        "risk_category": "HIGH",
        "section": "Part II — Special Conditions",
        "keywords": ["termination", "employer", "28 days cure", "performance security", "forfeiture"],
    },
    {
        "clause_id": "GCC-48",
        "clause_title": "Termination by Contractor",
        "clause_text": (
            "The Contractor may terminate if the Employer fails to pay within 56 days of due "
            "date, substantially fails its obligations, issues a prolonged suspension over "
            "84 days, or becomes insolvent. Upon Contractor termination, the Employer pays "
            "work executed, material costs, loss of profit, and demobilisation costs."
        ),
        "risk_category": "HIGH",
        "section": "Part II — Special Conditions",
        "keywords": ["termination", "contractor", "non-payment", "suspension", "demobilisation"],
    },
    {
        "clause_id": "GCC-49",
        "clause_title": "Liquidated Damages for Delay",
        "clause_text": (
            "If the Contractor fails to complete by the Time for Completion, Liquidated Damages "
            "shall be levied at the daily rate specified in the Contract Data. Total LD shall not "
            "exceed 10% of the Contract Price. LD is the sole remedy for delay and may be "
            "deducted from payments or recovered from Performance Security."
        ),
        "risk_category": "HIGH",
        "section": "Part II — Special Conditions",
        "keywords": ["liquidated damages", "LD", "delay", "10 percent", "time for completion"],
    },
    {
        "clause_id": "GCC-50",
        "clause_title": "Extension of Time for Completion",
        "clause_text": (
            "The Contractor is entitled to Extension of Time (EOT) for delays caused by "
            "Employer-issued Variations, force majeure, adverse physical conditions, or "
            "Employer's Personnel defaults. EOT notice must be submitted within 28 days "
            "of the delaying event. The Engineer assesses and grants a fair extension."
        ),
        "risk_category": "MEDIUM",
        "section": "Part II — Special Conditions",
        "keywords": ["extension of time", "EOT", "28 days notice", "force majeure", "variation"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Railway GCC clauses from PDF into a structured JSON file.",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Path to the official Railway GCC PDF file. If omitted, uses built-in seed data.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"Path to write the output JSON file. Default: {DEFAULT_OUTPUT}",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.pdf:
        if not Path(args.pdf).is_file():
            logger.error("PDF file not found: %s", args.pdf)
            sys.exit(1)

        logger.info("Mode: PDF extraction from %s", args.pdf)
        full_text = extract_text_from_pdf(args.pdf)
        clauses = extract_clauses_with_gemini(full_text)
        clauses = validate_and_clean(clauses)

        if not clauses:
            logger.error("No clauses were successfully extracted. Check Gemini API key and PDF content.")
            sys.exit(1)
    else:
        logger.info("No --pdf provided. Using built-in seed data (%d clauses).", len(GCC_SEED_CLAUSES))
        clauses = validate_and_clean(GCC_SEED_CLAUSES)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clauses, f, ensure_ascii=False, indent=2)

    logger.info("Successfully wrote %d clauses to: %s", len(clauses), output_path)
    print(f"\n✅ Done. {len(clauses)} clauses written to: {output_path}")


if __name__ == "__main__":
    main()
