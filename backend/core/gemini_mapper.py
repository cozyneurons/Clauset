"""
core/gemini_mapper.py

Gemini-powered contract-to-GCC clause mapping pipeline.

For each of the 3 contract parts:
  1. Build a structured prompt containing compact GCC metadata (IDs, titles,
     sections, keywords; not full texts).
  2. Send to Gemini with strict JSON schema enforcement.
  3. Gemini returns page-scoped anchors for every clause it detects in that part.

After all 3 parts complete:
  4. Merge results (deduplicate, collect multi-part matches).
  5. Run completeness check: set(all_gcc_ids) - set(found_ids) = missing candidates.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

try:
    from google import genai
    from google.genai import types as genai_types
    NEW_GENAI_SDK = True
except ImportError:
    import google.generativeai as genai
    NEW_GENAI_SDK = False
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Gemini model — read from env, default to gemini-1.5-flash ──
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# ── Backoff settings for rate-limit handling ──
MAX_RETRIES = 4
INITIAL_BACKOFF = 2.0   # seconds


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MappedClause:
    """Represents one clause found by Gemini in a contract part."""
    clause_id: str
    status: str               # "present" | "missing" (set by Gemini)
    page_number: int          # Approximate page in the PDF
    start_anchor: str         # Verbatim first ~7 words of the clause in the PDF text
    end_anchor: str           # Verbatim last ~7 words of the clause in the PDF text
    confidence: str           # "high" | "medium" | "low" (Gemini's self-rating)
    part_index: int           # Which part (0, 1, or 2) found this clause

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MappingResult:
    """Final merged result from all 3 Gemini calls."""
    found: Dict[str, MappedClause]    # clause_id → best MappedClause
    missing_candidates: List[str]     # clause_ids Gemini didn't find in any part
    part_errors: List[int]            # part indices that failed (for logging)


# ─────────────────────────────────────────────────────────────────────────────
# Gemini client initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _get_client():
    """Initialise and return the Gemini client."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in your .env file.")
    if NEW_GENAI_SDK:
        return genai.Client(api_key=api_key)

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.0,
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_mapping_prompt(
    part_text: str,
    part_index: int,
    total_parts: int,
    gcc_clause_index: List[Dict[str, Any]],
    part_page_start: int,
    part_page_end: int,
) -> str:
    """
    Build the mapping prompt for a single contract part.

    gcc_clause_index is a compact list of metadata dicts, NOT full clause
    texts, to keep prompt size small.
    """
    clause_index_str = json.dumps(gcc_clause_index, ensure_ascii=False)

    return f"""You are a senior legal analyst for Indian Railways contracts.

## Task
Scan the contract text excerpt below (Part {part_index + 1} of {total_parts}, pages {part_page_start}–{part_page_end})
and identify which of the listed Standard GCC clauses are referenced, addressed, or covered by the contract text.

## Standard GCC Clause Reference Index
{clause_index_str}

## Instructions
For each GCC clause that you can locate in the contract text:
- Use the clause title, section, and keywords to identify semantically equivalent contract clauses.
- Extract the verbatim FIRST 6–8 words of the matching clause text in the CONTRACT (not from the GCC list).
- Extract the verbatim LAST 6–8 words of the matching clause text in the CONTRACT.
- Record the approximate page number (from {part_page_start} to {part_page_end}).
- Rate your confidence: "high" if the clause is explicitly present, "medium" if implied/partial, "low" if uncertain.

## Output Format
Return a JSON array. Each element must have EXACTLY these fields:
{{
  "clause_id": "<GCC clause ID from the index above>",
  "status": "present",
  "page_number": <integer>,
  "start_anchor": "<verbatim first 6-8 words from the CONTRACT text>",
  "end_anchor": "<verbatim last 6-8 words from the CONTRACT text>",
  "confidence": "high" | "medium" | "low"
}}

Only include clauses that are PRESENT. Do NOT include clauses that are absent.
Return ONLY the JSON array — no markdown, no explanation.

## Contract Text (Part {part_index + 1} of {total_parts})
{part_text}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Single-part mapping call with retry/backoff
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini_with_backoff(
    client,
    prompt: str,
    part_index: int,
) -> Optional[str]:
    """
    Call Gemini with exponential backoff on rate limit or server errors.

    Returns the raw response text, or None on total failure.
    """
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Gemini call — Part %d, attempt %d/%d...", part_index + 1, attempt, MAX_RETRIES)
            if NEW_GENAI_SDK:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0,
                    ),
                )
            else:
                response = client.generate_content(prompt)
            logger.info("Gemini call — Part %d succeeded.", part_index + 1)
            return response.text.strip()
        except Exception as exc:
            err_str = str(exc).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str or "resource exhausted" in err_str:
                logger.warning(
                    "Rate limit hit on Part %d attempt %d. Retrying in %.1fs...",
                    part_index + 1, attempt, backoff
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)  # cap at 60 seconds
            else:
                logger.error("Gemini error on Part %d: %s", part_index + 1, exc)
                return None
    logger.error("Part %d: All %d attempts failed.", part_index + 1, MAX_RETRIES)
    return None


def _parse_part_response(
    raw: str,
    part_index: int,
) -> List[MappedClause]:
    """Parse Gemini's JSON response for one part into a list of MappedClause objects."""
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            logger.error("Part %d: Gemini returned non-list JSON.", part_index + 1)
            return []
    except json.JSONDecodeError as exc:
        logger.error("Part %d: JSON parse error — %s", part_index + 1, exc)
        return []

    clauses: List[MappedClause] = []
    for item in data:
        try:
            clauses.append(MappedClause(
                clause_id=str(item["clause_id"]).strip(),
                status=str(item.get("status", "present")).strip().lower(),
                page_number=int(item.get("page_number", 0)),
                start_anchor=str(item.get("start_anchor", "")).strip(),
                end_anchor=str(item.get("end_anchor", "")).strip(),
                confidence=str(item.get("confidence", "medium")).strip().lower(),
                part_index=part_index,
            ))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Part %d: Skipping malformed clause entry — %s", part_index + 1, exc)

    logger.info("Part %d: Parsed %d mapped clauses.", part_index + 1, len(clauses))
    return clauses


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def map_contract_to_gcc(
    contract_parts: List[List[Dict[str, Any]]],
    gcc_clauses: List[Dict[str, Any]],
) -> MappingResult:
    """
    Run the 3-part Gemini mapping pipeline.

    Args:
        contract_parts: Output of pdf_extractor.split_pages_into_parts() —
                        list of 3 sub-lists of {"page_num", "text", ...} dicts.
        gcc_clauses:    Full GCC clause list from gcc_clauses.json.

    Returns:
        MappingResult with:
          - found: dict mapping clause_id → MappedClause (best confidence pick)
          - missing_candidates: list of clause_ids not found in any part
          - part_errors: list of part indices that had API/parse failures
    """
    client = _get_client()

    # Build compact index for the prompt; full GCC text is reserved for Grok validation.
    gcc_clause_index = [
        {
            "clause_id": c["clause_id"],
            "clause_title": c["clause_title"],
            "section": c.get("section", ""),
            "keywords": c.get("keywords", [])[:8],
        }
        for c in gcc_clauses
    ]
    all_gcc_ids = {c["clause_id"] for c in gcc_clauses}

    # Accumulate raw matches from all 3 parts
    all_matches: List[MappedClause] = []
    part_errors: List[int] = []

    for part_idx, part_pages in enumerate(contract_parts):
        if not part_pages:
            logger.info("Part %d is empty — skipping.", part_idx + 1)
            continue

        # Concatenate page texts for this part
        part_text = "\n\n--- PAGE BREAK ---\n\n".join(p["text"] for p in part_pages)
        page_start = part_pages[0]["page_num"]
        page_end = part_pages[-1]["page_num"]

        prompt = _build_mapping_prompt(
            part_text=part_text,
            part_index=part_idx,
            total_parts=len(contract_parts),
            gcc_clause_index=gcc_clause_index,
            part_page_start=page_start,
            part_page_end=page_end,
        )

        raw = _call_gemini_with_backoff(client, prompt, part_idx)
        if raw is None:
            part_errors.append(part_idx)
            continue

        matches = _parse_part_response(raw, part_idx)
        all_matches.extend(matches)

    # ── Merge: for each clause_id, pick the highest-confidence match ──
    confidence_rank = {"high": 3, "medium": 2, "low": 1}

    found: Dict[str, MappedClause] = {}
    for match in all_matches:
        cid = match.clause_id
        if cid not in all_gcc_ids:
            logger.warning("Gemini returned unknown clause_id '%s' — ignoring.", cid)
            continue
        if cid not in found or confidence_rank.get(match.confidence, 0) > confidence_rank.get(found[cid].confidence, 0):
            found[cid] = match

    missing_candidates = sorted(all_gcc_ids - set(found.keys()))

    logger.info(
        "Mapping complete: %d found, %d missing candidates, %d part errors.",
        len(found),
        len(missing_candidates),
        len(part_errors),
    )
    return MappingResult(found=found, missing_candidates=missing_candidates, part_errors=part_errors)
