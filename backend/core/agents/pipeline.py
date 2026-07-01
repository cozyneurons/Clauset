"""
core/agents/pipeline.py

Orchestrates the Railway GCC contract analysis agent pipeline.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from core.agents.base_agent import AgentEvent
from core.agents.document_agent import DocumentAgent
from core.agents.gemini_validator_agent import GeminiValidatorAgent
from core.agents.mapper_agent import MapperAgent
from core.agents.validator_agent import ValidatorAgent

logger = logging.getLogger(__name__)


class ContractAnalysisPipeline:
    """
    Runs the full analysis pipeline:
      1. DocumentAgent parses the uploaded PDF.
      2. MapperAgent sends the 3 document parts to Gemini.
      3. ValidatorAgent extracts evidence and runs fuzzy fallback.
      4. GeminiValidatorAgent runs second-pass batch validation.
    """

    def __init__(self) -> None:
        self.document_agent = DocumentAgent()
        self.mapper_agent = MapperAgent()
        self.validator_agent = ValidatorAgent()
        self.gemini_validator_agent = GeminiValidatorAgent()

    def run(
        self,
        input_data: Dict[str, Any],
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Dict[str, Any]:
        pdf_path = input_data["pdf_path"]
        filename = input_data.get("filename", "")
        gcc_clauses: List[Dict[str, Any]] = input_data["gcc_clauses"]

        doc_output = self.document_agent.run({"pdf_path": pdf_path}, emit=emit)

        mapper_output = self.mapper_agent.run(
            {
                "parts": doc_output["parts"],
                "gcc_clauses": gcc_clauses,
            },
            emit=emit,
        )

        validator_output = self.validator_agent.run(
            {
                "mapping": mapper_output["mapping"],
                "pages": doc_output["pages"],
                "full_text": doc_output["full_text"],
                "gcc_clauses": gcc_clauses,
            },
            emit=emit,
        )

        gemini_output = self.gemini_validator_agent.run(
            input_data={
                "clause_results": validator_output["clause_results"],
            },
            emit=emit,
        )
        clause_results = gemini_output["clause_results"]
        found_count = sum(
            1
            for clause in clause_results
            if clause.get("final_status", clause.get("status")) in {"present", "present_fuzzy"}
        )
        missing_count = sum(
            1
            for clause in clause_results
            if clause.get("final_status", clause.get("status")) == "truly_missing"
        )
        needs_review_count = sum(
            1
            for clause in clause_results
            if clause.get("final_status") == "needs_review"
        )

        return {
            "filename": filename,
            "page_count": doc_output["page_count"],
            "total_gcc_clauses": len(gcc_clauses),
            "found_count": found_count,
            "missing_count": missing_count,
            "needs_review_count": needs_review_count,
            "part_errors": mapper_output["mapping"].part_errors,
            "gemini_summary": gemini_output["gemini_summary"],
            "clauses": clause_results,
        }
