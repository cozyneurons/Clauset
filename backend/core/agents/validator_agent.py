"""
core/agents/validator_agent.py

Agent 3 — Fuzzy Validator Agent
Wraps clause_matcher.py logic to validate and extract verbatim text.
"""

from typing import Any, Callable, Dict, List, Optional

from core.agents.base_agent import BaseAgent, AgentEvent
from core.gemini_mapper import MappingResult
from core.clause_matcher import extract_verbatim_text, fuzzy_search_missing


class ValidatorAgent(BaseAgent):
    """
    Extracts verbatim text for found clauses and runs fuzzy fallback for missing ones.

    Input: {
        "mapping": MappingResult,
        "pages": List[Dict],
        "full_text": str,
        "gcc_clauses": List[Dict],
    }
    Output: {
        "clause_results": List[Dict]  — unified list with status, verbatim text, etc.
    }
    """

    name = "FuzzyValidator"

    def run(
        self,
        input_data: Dict[str, Any],
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Dict[str, Any]:
        mapping: MappingResult = input_data["mapping"]
        pages = input_data["pages"]
        full_text = input_data["full_text"]
        gcc_clauses = input_data["gcc_clauses"]

        gcc_lookup: Dict[str, Dict[str, Any]] = {c["clause_id"]: c for c in gcc_clauses}

        self._emit(emit, "started", 0, f"Validating {len(mapping.found)} found clauses...")

        # ── Extract verbatim text for found clauses ──
        clause_results: List[Dict[str, Any]] = []
        found_items = list(mapping.found.items())

        for i, (cid, mapped) in enumerate(found_items):
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
                "part_index": mapped.part_index,
                "start_anchor": mapped.start_anchor,
                "end_anchor": mapped.end_anchor,
                "verbatim_text": verbatim or "",
                "gcc_text": gcc_meta.get("clause_text", ""),
                "matched_keywords": [],
            })

            if (i + 1) % 10 == 0:
                pct = int(30 + (i / len(found_items)) * 40)
                self._emit(emit, "running", pct, f"Extracted text for {i + 1}/{len(found_items)} clauses...")

        self._emit(emit, "running", 70, f"Running fuzzy search for {len(mapping.missing_candidates)} missing candidates...")

        # ── Fuzzy fallback for missing candidates ──
        fuzzy_results = fuzzy_search_missing(
            missing_ids=mapping.missing_candidates,
            gcc_clauses=gcc_clauses,
            full_text=full_text,
        )

        for cid, fuzzy_data in fuzzy_results.items():
            gcc_meta = gcc_lookup.get(cid, {})
            clause_results.append({
                "clause_id": cid,
                "clause_title": gcc_meta.get("clause_title", ""),
                "risk_category": gcc_meta.get("risk_category", "MEDIUM"),
                "section": gcc_meta.get("section", ""),
                "status": fuzzy_data["status"],
                "page_number": None,
                "confidence": "low" if fuzzy_data["status"] == "present_fuzzy" else None,
                "part_index": None,
                "start_anchor": "",
                "end_anchor": "",
                "verbatim_text": fuzzy_data.get("context") or "",
                "gcc_text": gcc_meta.get("clause_text", ""),
                "matched_keywords": fuzzy_data.get("matched_keywords", []),
            })

        # ── Sort: present first, then present_fuzzy, then truly_missing ──
        status_order = {"present": 0, "present_fuzzy": 1, "truly_missing": 2}
        clause_results.sort(key=lambda x: (status_order.get(x["status"], 3), x["clause_id"]))

        present_count = sum(1 for c in clause_results if c["status"] in ("present", "present_fuzzy"))
        missing_count = sum(1 for c in clause_results if c["status"] == "truly_missing")

        self._emit(emit, "complete", 100, f"Validation complete: {present_count} present, {missing_count} missing.", {
            "present_count": present_count,
            "missing_count": missing_count,
        })

        return {"clause_results": clause_results}
