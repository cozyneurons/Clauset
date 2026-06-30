"""
core/groq_client.py

Groq LLM API client for the Railway GCC Contract Risk Analyzer.
All API calls use the requests library (no openai SDK).

Implements:
  - analyze_clause()         — single-clause analysis (used as fallback)
  - analyze_clauses_batch()  — primary batched analysis (up to 3 clauses per call)
  - summarize_full_report()  — executive summary generation
"""

import os
import json
import time
import logging
import re
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)

# Safe error dict returned when analysis fails
_ERROR_ANALYSIS = {
    "risk_level": "LOW",
    "summary": "Analysis could not be completed due to an API error. Please review this clause manually.",
    "deviations": ["Could not assess deviations — API error."],
    "recommendations": ["Manually review this clause with a qualified legal expert."],
    "relevant_clause_ids": [],
}


class GroqAnalyzer:
    """
    Wraps the Groq Chat Completions API (OpenAI-compatible) using the
    requests library to analyse Railway contract clauses against GCC rules.
    """

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.1-8b-instant"
    MAX_TOKENS = 1024
    BATCH_SIZE_LIMIT = 3

    SYSTEM_PROMPT = (
        "You are a senior Railway contract legal expert with over 20 years of experience "
        "in Indian Railways General Conditions of Contract (GCC). Your role is to analyse "
        "contract clauses submitted by a user, compare them against the official Railway GCC "
        "rules provided, and identify risks, deviations, and non-compliant terms. "
        "You must always respond in valid, parseable JSON. Do not include markdown code fences, "
        "explanatory text, or anything outside the JSON structure in your response."
    )

    def __init__(self) -> None:
        """
        Initialise the GroqAnalyzer.

        Reads GROQ_API_KEY from environment variables. Raises RuntimeError
        if the key is not set.
        """
        self.api_key: str = os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "GROQ_API_KEY environment variable is not set. "
                "API calls will fail. Set it in your .env file."
            )
        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_groq(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Make a single API call to the Groq Chat Completions endpoint.
        Implements automatic retries with backoff on rate limits (HTTP 429).

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            The content string of the assistant's reply, or None on failure.
        """
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "max_tokens": self.MAX_TOKENS,
            "temperature": 0.1,  # Low temperature for deterministic, structured output
        }

        max_retries = 3
        backoff_delay = 2.0

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.GROQ_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=90,
                )
                
                # Check for rate limit explicitly
                if response.status_code == 429:
                    error_data = response.json()
                    err_msg = error_data.get("error", {}).get("message", "")
                    
                    # Parse the retry time if provided (e.g., "Please try again in 1.07s.")
                    sleep_time = 3.0
                    match = re.search(r"try again in (\d+(?:\.\d+)?)s", err_msg)
                    if match:
                        sleep_time = float(match.group(1)) + 0.5 # Add a small buffer
                    
                    logger.warning(
                        "Rate limit hit (429). Retrying attempt %d/%d after sleeping %.2fs...",
                        attempt + 1, max_retries, sleep_time
                    )
                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()
                data = response.json()
                content: str = data["choices"][0]["message"]["content"]
                return content
            except requests.exceptions.HTTPError as exc:
                # If we got a 429 we already handled it above, for other HTTP errors we fail
                if response.status_code == 429:
                    continue
                logger.error("Groq API HTTP error: %s — %s", exc, response.text)
                return None
            except requests.exceptions.Timeout:
                logger.warning("Groq API request timed out. Retrying...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
            except (KeyError, IndexError) as exc:
                logger.error("Unexpected Groq API response structure: %s", exc)
                return None
            except Exception as exc:
                logger.error("Groq API call failed: %s", exc)
                return None
        
        logger.error("Failed to call Groq API after %d attempts due to rate limits.", max_retries)
        return None

    def _extract_json(self, raw: str) -> Any:
        """
        Robustly extract JSON from the raw LLM response.

        The LLM sometimes wraps output in markdown fences or adds extra text.
        This method strips such decorations before parsing.

        Args:
            raw: Raw string returned by the LLM.

        Returns:
            Parsed Python object (dict or list), or raises ValueError on failure.
        """
        # Remove markdown code fences if present
        stripped = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```\s*$", "", stripped).strip()

        # Find the outermost JSON object or array
        json_match = re.search(r"(\[.*\]|\{.*\})", stripped, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        return json.loads(stripped)

    def _format_gcc_rules_block(self, matched_rules: List[Dict[str, Any]]) -> str:
        """
        Format matched GCC rules as a readable block for the prompt.

        Args:
            matched_rules: List of rule metadata dicts from ChromaDB.

        Returns:
            Formatted string block.
        """
        if not matched_rules:
            return "No matching GCC rules found for this clause."

        lines = []
        for rule in matched_rules:
            lines.append(
                f"  Clause ID : {rule.get('clause_id', 'N/A')}\n"
                f"  Title     : {rule.get('clause_title', 'N/A')}\n"
                f"  Risk Level: {rule.get('risk_category', 'N/A')}\n"
                f"  Keywords  : {rule.get('keywords', 'N/A')}"
            )
        return "\n\n".join(lines)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_clause(
        self,
        extracted_chunk: str,
        matched_gcc_rules: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyse a single contract clause against matched GCC rules.

        This method is the fallback for individual clause analysis. The primary
        method is analyze_clauses_batch(). Use this only when batching fails.

        Args:
            extracted_chunk:   The extracted clause text from the uploaded contract.
            matched_gcc_rules: GCC rules from ChromaDB that are semantically similar
                               to the extracted chunk.

        Returns:
            A dict with keys: risk_level, summary, deviations,
            recommendations, relevant_clause_ids.
        """
        gcc_block = self._format_gcc_rules_block(matched_gcc_rules)

        user_prompt = (
            "Analyse the following contract clause against the provided Railway GCC rules "
            "and respond in the exact JSON format specified.\n\n"
            "=== SECTION A: EXTRACTED CLAUSE FROM UPLOADED CONTRACT ===\n"
            f"{extracted_chunk.strip()}\n\n"
            "=== SECTION B: MATCHING OFFICIAL RAILWAY GCC RULES ===\n"
            f"{gcc_block}\n\n"
            "Respond ONLY with a single JSON object in this format:\n"
            "{\n"
            '  "risk_level": "HIGH" | "MEDIUM" | "LOW" | "COMPLIANT",\n'
            '  "summary": "one paragraph plain English summary of your findings",\n'
            '  "deviations": ["specific deviation 1", "specific deviation 2"],\n'
            '  "recommendations": ["actionable fix 1", "actionable fix 2"],\n'
            '  "relevant_clause_ids": ["GCC-X.X", "GCC-X.X"]\n'
            "}"
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = self._call_groq(messages)

        if raw_response is None:
            logger.warning("Groq returned no response for single clause analysis.")
            return dict(_ERROR_ANALYSIS)

        try:
            result = self._extract_json(raw_response)
            if isinstance(result, dict):
                return result
            logger.warning("Groq response was not a dict: %s", type(result))
            return dict(_ERROR_ANALYSIS)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse Groq single-clause response: %s", exc)
            return dict(_ERROR_ANALYSIS)

    def analyze_clauses_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyse a batch of up to 3 contract clauses in a single Groq API call.

        This is the PRIMARY analysis method. Batching reduces API calls by ~70%
        compared to calling analyze_clause() individually, keeping the app within
        Groq's free-tier rate limit of ~6,000 tokens/minute.

        Args:
            batch: A list of dicts (max 3), each with:
                   - "chunk_text"   : str — extracted clause text
                   - "chunk_label"  : str — human-readable label, e.g. "Clause 47"
                   - "matched_rules": list[dict] — GCC rules from ChromaDB

        Returns:
            A list of analysis dicts (same format as analyze_clause()).
            Falls back to individual calls if batch parsing fails.
        """
        # Hard limit: never send more than 3 clauses per batch
        batch = batch[: self.BATCH_SIZE_LIMIT]
        n = len(batch)

        if n == 0:
            return []

        if n == 1:
            # No benefit in batching a single clause — call directly
            item = batch[0]
            return [self.analyze_clause(item["chunk_text"], item["matched_rules"])]

        # Build the combined batch prompt
        clause_blocks = []
        for idx, item in enumerate(batch, start=1):
            gcc_block = self._format_gcc_rules_block(item["matched_rules"])
            clause_blocks.append(
                f"=== CLAUSE {idx}: {item.get('chunk_label', f'Chunk {idx}')} ===\n"
                f"EXTRACTED TEXT:\n{item['chunk_text'].strip()}\n\n"
                f"MATCHING GCC RULES:\n{gcc_block}"
            )

        combined_clauses = "\n\n".join(clause_blocks)

        user_prompt = (
            f"Analyse the following {n} contract clauses against the provided Railway GCC rules. "
            f"Respond ONLY with a JSON array containing exactly {n} objects "
            "(one per clause, in order). Each object must follow this schema:\n"
            "{\n"
            '  "risk_level": "HIGH" | "MEDIUM" | "LOW" | "COMPLIANT",\n'
            '  "summary": "plain English paragraph",\n'
            '  "deviations": ["deviation 1", "deviation 2"],\n'
            '  "recommendations": ["fix 1", "fix 2"],\n'
            '  "relevant_clause_ids": ["GCC-X.X"]\n'
            "}\n\n"
            f"{combined_clauses}\n\n"
            f"Respond ONLY with a JSON array of exactly {n} objects. No other text."
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = self._call_groq(messages)

        if raw_response is not None:
            try:
                result = self._extract_json(raw_response)
                if isinstance(result, list) and len(result) == n:
                    logger.info("Batch of %d clauses parsed successfully.", n)
                    return result
                elif isinstance(result, list):
                    logger.warning(
                        "Batch response has %d items but expected %d. "
                        "Falling back to individual calls.",
                        len(result),
                        n,
                    )
                else:
                    logger.warning(
                        "Batch response is not a list (%s). Falling back.", type(result)
                    )
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Batch JSON parse failed (%s). Falling back to individual calls.", exc
                )

        # Fallback: call analyze_clause() individually for each item
        logger.info("Executing individual fallback analysis for %d clauses.", n)
        results = []
        for item in batch:
            individual = self.analyze_clause(item["chunk_text"], item["matched_rules"])
            results.append(individual)
            # Brief sleep between individual fallback calls to respect rate limits
            time.sleep(0.5)
        return results

    def summarize_full_report(self, all_analyses: List[Dict[str, Any]]) -> str:
        """
        Generate an executive summary paragraph covering all analysed clauses.

        Args:
            all_analyses: List of individual clause analysis dicts returned by
                          analyze_clause() or analyze_clauses_batch().

        Returns:
            A plain-text executive summary string. Returns a fallback message
            on API failure.
        """
        if not all_analyses:
            return (
                "No clauses were analysed. Please upload a valid contract PDF and retry."
            )

        # Summarise the risk profile for the prompt
        risk_counts: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "COMPLIANT": 0}
        all_deviations: List[str] = []
        for analysis in all_analyses:
            level = analysis.get("risk_level", "LOW")
            if level in risk_counts:
                risk_counts[level] += 1
            all_deviations.extend(analysis.get("deviations", []))

        risk_summary = ", ".join(
            f"{count} {level}" for level, count in risk_counts.items() if count > 0
        )
        top_deviations = all_deviations[:10]  # limit to top 10 for prompt size

        user_prompt = (
            "You have completed a clause-by-clause risk analysis of a Railway contract "
            "against the official Indian Railways General Conditions of Contract (GCC).\n\n"
            f"Risk profile: {risk_summary} clauses identified.\n"
            f"Key deviations found:\n" +
            "\n".join(f"  - {d}" for d in top_deviations) +
            "\n\n"
            "Write a single executive summary paragraph (4-6 sentences) in plain English "
            "that a senior project manager or legal counsel could use to understand the "
            "overall risk posture of this contract. Highlight the most critical risks and "
            "recommend immediate actions. Do NOT include JSON or any formatting — just "
            "plain prose."
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = self._call_groq(messages)

        if raw_response is None:
            return (
                "Executive summary could not be generated due to an API error. "
                "Please review the individual clause analyses in the sections below."
            )

        # Strip any accidental JSON or markdown from the summary
        summary = raw_response.strip()
        summary = re.sub(r"```.*?```", "", summary, flags=re.DOTALL).strip()
        return summary
