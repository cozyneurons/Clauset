"""
core/clause_matcher.py

Two-stage fallback matcher for clauses flagged as "missing" by Gemini.

Stage 1 — Page-scoped anchor extraction:
    For "present" clauses, uses the page_number + fuzzy substring search
    to extract verbatim contract text from the PDF pages.

Stage 2 — Fuzzy keyword fallback for "missing" candidates:
    For each clause_id NOT found by Gemini, runs a rapidfuzz keyword search
    across the full contract text using the clause's keywords from gcc_clauses.json.
    Upgrades the status from "missing_candidate" to "present_fuzzy" if found,
    or confirms "truly_missing" if not.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from rapidfuzz import fuzz

from core.gemini_mapper import MappedClause

logger = logging.getLogger(__name__)

# Minimum fuzzy score (0–100) to consider a keyword a match
FUZZY_KEYWORD_THRESHOLD = 75
# Minimum number of keywords that must match to upgrade to "present_fuzzy"
MIN_KEYWORD_HITS = 2

# How many words to include in context window around a matched anchor
CONTEXT_WORDS = 300


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Verbatim text extraction from anchors
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _fuzzy_find_anchor(
    page_text: str,
    anchor: str,
    threshold: int = 80,
) -> Optional[int]:
    """
    Find the start character index of `anchor` within `page_text` using
    a sliding window fuzzy match. Returns None if no match above threshold.
    """
    if not anchor or not page_text:
        return None

    norm_page = _normalize(page_text)
    norm_anchor = _normalize(anchor)
    anchor_len = len(norm_anchor)

    if anchor_len == 0:
        return None

    best_score = 0
    best_pos = None

    # Slide a window of anchor_len ± 20% across the normalized page text
    window = max(anchor_len, 1)
    for start in range(0, max(1, len(norm_page) - window + 1)):
        end = min(start + window, len(norm_page))
        snippet = norm_page[start:end]
        score = fuzz.partial_ratio(norm_anchor, snippet)
        if score > best_score:
            best_score = score
            best_pos = start

    if best_score >= threshold:
        return best_pos
    return None


def extract_verbatim_text(
    mapped_clause: MappedClause,
    pages: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Extract the verbatim contract text for a mapped clause using its page anchors.

    Strategy:
      1. Scope to the clause's page and the next page (handles cross-page clauses).
      2. Fuzzy-find start_anchor position in the scoped text.
      3. Fuzzy-find end_anchor position after the start.
      4. If end_anchor not found, fall back to extracting CONTEXT_WORDS words from start.
      5. If start_anchor not found, fall back to returning the entire scoped page text.

    Args:
        mapped_clause: A MappedClause with page_number, start_anchor, end_anchor.
        pages:         The full list of per-page dicts from extract_pages().

    Returns:
        The verbatim extracted text string, or None if extraction completely fails.
    """
    page_num = mapped_clause.page_number
    # Build scoped text: target page + next page (to handle cross-page clauses)
    scoped_pages = [p for p in pages if p["page_num"] in (page_num, page_num + 1)]
    if not scoped_pages:
        # Expand scope to ±1 around the page number
        scoped_pages = [p for p in pages if abs(p["page_num"] - page_num) <= 1]
    if not scoped_pages:
        logger.warning("Clause %s: no pages found around page %d.", mapped_clause.clause_id, page_num)
        return None

    scoped_text = "\n".join(p["text"] for p in scoped_pages)

    # Try to locate start anchor
    start_pos = _fuzzy_find_anchor(scoped_text, mapped_clause.start_anchor)

    if start_pos is None:
        logger.warning(
            "Clause %s: start_anchor not found (page %d). Returning full page text.",
            mapped_clause.clause_id, page_num
        )
        return scoped_pages[0]["text"].strip()

    # Try to locate end anchor after start_pos
    search_from = start_pos + len(mapped_clause.start_anchor)
    remaining = scoped_text[search_from:]
    end_offset = _fuzzy_find_anchor(remaining, mapped_clause.end_anchor)

    if end_offset is not None:
        end_pos = search_from + end_offset + len(mapped_clause.end_anchor)
        extracted = scoped_text[start_pos:end_pos].strip()
        logger.debug("Clause %s: extracted %d chars using anchors.", mapped_clause.clause_id, len(extracted))
        return extracted
    else:
        # Fallback: extract CONTEXT_WORDS words from start position
        logger.info(
            "Clause %s: end_anchor not found. Using %d-word fallback from start.",
            mapped_clause.clause_id, CONTEXT_WORDS
        )
        words = scoped_text[start_pos:].split()
        return " ".join(words[:CONTEXT_WORDS]).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Fuzzy keyword fallback for missing candidates
# ─────────────────────────────────────────────────────────────────────────────

def _keyword_hits(text: str, keywords: List[str]) -> List[str]:
    """Return the list of keywords that fuzzy-match within the text."""
    norm_text = _normalize(text)
    hits = []
    for kw in keywords:
        score = fuzz.partial_ratio(_normalize(kw), norm_text)
        if score >= FUZZY_KEYWORD_THRESHOLD:
            hits.append(kw)
    return hits


def fuzzy_search_missing(
    missing_ids: List[str],
    gcc_clauses: List[Dict[str, Any]],
    full_text: str,
) -> Dict[str, Dict[str, Any]]:
    """
    Run fuzzy keyword search for clauses flagged as missing by Gemini.

    For each missing clause_id:
      - Look up its keywords from gcc_clauses.
      - Run rapidfuzz partial_ratio on the full contract text.
      - If MIN_KEYWORD_HITS or more keywords match, upgrade to "present_fuzzy".
      - Otherwise, confirm as "truly_missing".

    Args:
        missing_ids:  List of clause_ids that Gemini did not find.
        gcc_clauses:  Full GCC clause list (to access keywords).
        full_text:    The full contract text (all pages joined).

    Returns:
        Dict mapping clause_id → {
            "status": "present_fuzzy" | "truly_missing",
            "matched_keywords": [...],
            "context": <short snippet around first keyword match, if present_fuzzy>
        }
    """
    # Build a lookup for keyword retrieval
    gcc_lookup: Dict[str, Dict[str, Any]] = {c["clause_id"]: c for c in gcc_clauses}
    results: Dict[str, Dict[str, Any]] = {}

    for cid in missing_ids:
        if cid not in gcc_lookup:
            logger.warning("Missing candidate '%s' not found in GCC reference data.", cid)
            results[cid] = {"status": "truly_missing", "matched_keywords": [], "context": None}
            continue

        clause = gcc_lookup[cid]
        keywords: List[str] = clause.get("keywords", [])

        if not keywords:
            logger.info("Clause %s has no keywords — confirming truly_missing.", cid)
            results[cid] = {"status": "truly_missing", "matched_keywords": [], "context": None}
            continue

        hits = _keyword_hits(full_text, keywords)

        if len(hits) >= MIN_KEYWORD_HITS:
            # Find a short context snippet around the first matched keyword
            first_kw = _normalize(hits[0])
            idx = _normalize(full_text).find(first_kw[:20])  # search on first 20 chars
            context = None
            if idx != -1:
                words = full_text[max(0, idx - 100): idx + 300].split()
                context = " ".join(words[:60]).strip()

            logger.info(
                "Clause %s: UPGRADED to present_fuzzy (%d/%d keywords matched).",
                cid, len(hits), len(keywords)
            )
            results[cid] = {
                "status": "present_fuzzy",
                "matched_keywords": hits,
                "context": context,
            }
        else:
            logger.info(
                "Clause %s: confirmed TRULY MISSING (%d/%d keywords matched).",
                cid, len(hits), len(keywords)
            )
            results[cid] = {
                "status": "truly_missing",
                "matched_keywords": hits,
                "context": None,
            }

    return results
