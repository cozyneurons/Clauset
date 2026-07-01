"""
core/agents/gemini_validator_agent.py

Agent 4 - Gemini Validator Agent
Runs a second LLM pass over clause results using Gemini to validate findings.
Splits all records into exactly 2 batches and waits 60 seconds before executing 
to ensure the first-pass Gemini rate limits have reset.
"""

import json
import logging
import os
import time
import math
from typing import Any, Callable, Dict, List, Optional

try:
    from google import genai
    from google.genai import types as genai_types
    NEW_GENAI_SDK = True
except ImportError:
    import google.generativeai as genai
    NEW_GENAI_SDK = False
from dotenv import load_dotenv

from core.agents.base_agent import AgentEvent, BaseAgent

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_MAX_RETRIES = 4
GEMINI_INITIAL_BACKOFF = 2.0


def _enabled() -> bool:
    return os.getenv("GEMINI_VALIDATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return ""
    return api_key


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return f"{text[:head]}\n...[truncated]...\n{text[-tail:]}"


class GeminiValidatorAgent(BaseAgent):
    """
    Validates Gemini/fuzzy clause findings with a second pass via Gemini.

    Input: {
        "clause_results": List[Dict],
    }

    Output: {
        "clause_results": List[Dict],
        "gemini_summary": Dict,
    }
    """

    name = "GeminiValidator"

    def run(
        self,
        input_data: Dict[str, Any],
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Dict[str, Any]:
        clause_results = list(input_data["clause_results"])

        if not _enabled():
            self._emit(emit, "complete", 100, "Gemini validation disabled by environment.")
            return self._mark_skipped(clause_results, "disabled")

        api_key = _get_api_key()
        if not api_key:
            self._emit(emit, "complete", 100, "Gemini validation skipped: GEMINI_API_KEY is not set.")
            return self._mark_skipped(clause_results, "missing_api_key")

        self._emit(
            emit,
            "started",
            0,
            "Waiting 60 seconds to reset Gemini API rate limits...",
            {"waiting_seconds": 60},
        )
        time.sleep(60)

        # Force exactly 2 batches
        total_clauses = len(clause_results)
        batch_size = math.ceil(total_clauses / 2) if total_clauses > 0 else 1
        batches = [
            clause_results[i : i + batch_size]
            for i in range(0, total_clauses, batch_size)
        ]

        self._emit(
            emit,
            "running",
            10,
            f"Starting Gemini validation across {len(batches)} batches...",
            {"batch_count": len(batches), "batch_size": batch_size},
        )

        validations: Dict[str, Dict[str, Any]] = {}
        batch_errors: List[Dict[str, Any]] = []
        client = self._get_client(api_key)

        for idx, batch in enumerate(batches):
            if not batch:
                continue
                
            pct = 10 + int((idx / max(len(batches), 1)) * 80)
            self._emit(emit, "running", pct, f"Validating batch {idx + 1}/{len(batches)} with Gemini...")

            try:
                batch_validations = self._validate_batch(client, batch, idx)
                validations.update(batch_validations)
            except Exception as exc:
                logger.exception("Gemini validation batch %d failed.", idx + 1)
                batch_errors.append({"batch_index": idx, "error": str(exc)})
                for clause in batch:
                    validations[clause["clause_id"]] = {
                        "gemini_status": "needs_review",
                        "gemini_confidence": "low",
                        "gemini_reason": f"Gemini validation failed for this batch: {exc}",
                        "final_status": clause.get("status", "needs_review"),
                    }

        merged = self._merge_validations(clause_results, validations)
        summary = self._summarize(merged, batch_errors)

        self._emit(
            emit,
            "complete",
            100,
            "Gemini validation complete.",
            summary,
        )

        return {
            "clause_results": merged,
            "gemini_summary": summary,
        }

    def _mark_skipped(self, clause_results: List[Dict[str, Any]], reason: str) -> Dict[str, Any]:
        for clause in clause_results:
            clause["gemini_status"] = "skipped"
            clause["gemini_confidence"] = None
            clause["gemini_reason"] = reason
            clause["final_status"] = clause.get("status")

        return {
            "clause_results": clause_results,
            "gemini_summary": {
                "enabled": _enabled(),
                "status": "skipped",
                "reason": reason,
                "model": GEMINI_MODEL,
                "validated_count": 0,
                "needs_review_count": 0,
                "batch_errors": [],
            },
        }

    def _validate_batch(
        self,
        client,
        batch: List[Dict[str, Any]],
        batch_index: int,
    ) -> Dict[str, Dict[str, Any]]:
        prompt = self._build_prompt(batch)
        
        system_instruction = (
            "You are a careful Indian Railways contract analyst. "
            "Validate whether the contract evidence supports each proposed GCC clause match. "
            "Return strict JSON only."
        )
        
        backoff = GEMINI_INITIAL_BACKOFF
        last_error = None
        
        for attempt in range(1, GEMINI_MAX_RETRIES + 1):
            try:
                if NEW_GENAI_SDK:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            temperature=0.0,
                        ),
                    )
                else:
                    response = client.generate_content(prompt)
                if not response.text:
                    raise ValueError("Gemini returned empty text")
                return self._parse_response(response.text, batch, batch_index)
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                if "quota" in err_str or "rate" in err_str or "429" in err_str or "resource exhausted" in err_str:
                    logger.warning(
                        "Rate limit hit on Validation Batch %d attempt %d. Retrying in %.1fs...",
                        batch_index + 1, attempt, backoff
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                else:
                    if attempt < GEMINI_MAX_RETRIES:
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                    else:
                        raise RuntimeError(f"Gemini validation failed after {GEMINI_MAX_RETRIES} attempts: {last_error}")

        raise RuntimeError(f"Gemini validation failed after {GEMINI_MAX_RETRIES} attempts: {last_error}")

    def _get_client(self, api_key: str):
        if NEW_GENAI_SDK:
            return genai.Client(api_key=api_key)

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=(
                "You are a careful Indian Railways contract analyst. "
                "Validate whether the contract evidence supports each proposed GCC clause match. "
                "Return strict JSON only."
            ),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

    def _build_prompt(self, batch: List[Dict[str, Any]]) -> str:
        records = []
        for clause in batch:
            records.append({
                "clause_id": clause.get("clause_id"),
                "clause_title": clause.get("clause_title"),
                "risk_category": clause.get("risk_category"),
                "initial_status": clause.get("status"),
                "page_number": clause.get("page_number"),
                "initial_confidence": clause.get("confidence"),
                "matched_keywords": clause.get("matched_keywords", []),
                "gcc_clause_text": _truncate(clause.get("gcc_text", ""), 2500),
                "contract_evidence": _truncate(clause.get("verbatim_text", ""), 2500),
            })

        return (
            "Validate this batch of Railway GCC clause findings.\n\n"
            "For each record, compare gcc_clause_text with contract_evidence.\n"
            "Use the initial_status as a hint, not as proof.\n\n"
            "Decision rules:\n"
            "- confirmed_present: contract_evidence clearly covers the GCC clause.\n"
            "- partially_supported: contract_evidence covers only part of the GCC clause or is ambiguous.\n"
            "- not_supported: initial_status says present but the evidence does not support that clause.\n"
            "- confirmed_missing: initial_status is truly_missing and no evidence is provided.\n"
            "- needs_review: evidence is too weak, noisy OCR text, or legal judgment is uncertain.\n\n"
            "Return a JSON object with exactly this shape:\n"
            "{\n"
            '  "validations": [\n'
            "    {\n"
            '      "clause_id": "same id as input",\n'
            '      "gemini_status": "confirmed_present | partially_supported | not_supported | confirmed_missing | needs_review",\n'
            '      "gemini_confidence": "high | medium | low",\n'
            '      "gemini_reason": "one concise sentence",\n'
            '      "final_status": "present | present_fuzzy | truly_missing | needs_review"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Batch records:\n"
            f"{json.dumps(records, ensure_ascii=False)}"
        )

    def _parse_response(
        self,
        content: str,
        batch: List[Dict[str, Any]],
        batch_index: int,
    ) -> Dict[str, Dict[str, Any]]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON for batch {batch_index + 1}: {exc}") from exc

        raw_validations = parsed.get("validations")
        if not isinstance(raw_validations, list):
            raise ValueError("JSON did not include a validations array")

        expected_ids = {str(item["clause_id"]) for item in batch}
        validations: Dict[str, Dict[str, Any]] = {}

        for item in raw_validations:
            cid = str(item.get("clause_id", "")).strip()
            if cid not in expected_ids:
                logger.warning("Returned unexpected clause_id '%s' in batch %d.", cid, batch_index + 1)
                continue

            validations[cid] = {
                "gemini_status": self._clean_choice(
                    item.get("gemini_status"),
                    {"confirmed_present", "partially_supported", "not_supported", "confirmed_missing", "needs_review"},
                    "needs_review",
                ),
                "gemini_confidence": self._clean_choice(
                    item.get("gemini_confidence"),
                    {"high", "medium", "low"},
                    "low",
                ),
                "gemini_reason": str(item.get("gemini_reason", "")).strip()[:500],
                "final_status": self._clean_choice(
                    item.get("final_status"),
                    {"present", "present_fuzzy", "truly_missing", "needs_review"},
                    "needs_review",
                ),
            }

        for missing_id in expected_ids - set(validations.keys()):
            validations[missing_id] = {
                "gemini_status": "needs_review",
                "gemini_confidence": "low",
                "gemini_reason": "Gemini did not return a validation for this clause.",
                "final_status": "needs_review",
            }

        return validations

    def _merge_validations(
        self,
        clause_results: List[Dict[str, Any]],
        validations: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        merged = []
        for clause in clause_results:
            updated = dict(clause)
            validation = validations.get(clause["clause_id"])
            if validation:
                updated.update(validation)
            else:
                updated.update({
                    "gemini_status": "needs_review",
                    "gemini_confidence": "low",
                    "gemini_reason": "Clause was not sent to Gemini validation.",
                    "final_status": clause.get("status", "needs_review"),
                })
            merged.append(updated)
        return merged

    def _summarize(
        self,
        clause_results: List[Dict[str, Any]],
        batch_errors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for clause in clause_results:
            status = clause.get("gemini_status", "unknown")
            counts[status] = counts.get(status, 0) + 1

        return {
            "enabled": _enabled(),
            "status": "complete" if not batch_errors else "partial",
            "model": GEMINI_MODEL,
            "validated_count": len(clause_results),
            "needs_review_count": counts.get("needs_review", 0),
            "status_counts": counts,
            "batch_errors": batch_errors,
        }

    @staticmethod
    def _clean_choice(value: Any, allowed: set, fallback: str) -> str:
        value = str(value or "").strip().lower()
        return value if value in allowed else fallback
