"""
core/agents/mapper_agent.py

Agent 2 — Structural Mapper Agent (Gemini)
Wraps the 3-part Gemini mapping pipeline from gemini_mapper.py.
"""

from typing import Any, Callable, Dict, List, Optional

from core.agents.base_agent import BaseAgent, AgentEvent
from core.gemini_mapper import map_contract_to_gcc, MappingResult


class MapperAgent(BaseAgent):
    """
    Sends 3 contract parts to Gemini to identify which GCC clauses are present.

    Input:  {"parts": List[List[Dict]], "gcc_clauses": List[Dict]}
    Output: {"mapping": MappingResult}
    """

    name = "StructuralMapper"

    def run(
        self,
        input_data: Dict[str, Any],
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Dict[str, Any]:
        parts = input_data["parts"]
        gcc_clauses = input_data["gcc_clauses"]

        self._emit(emit, "started", 0, f"Starting Gemini mapping across {len(parts)} contract parts...")

        mapping: MappingResult = map_contract_to_gcc(parts, gcc_clauses)

        found_count = len(mapping.found)
        missing_count = len(mapping.missing_candidates)

        self._emit(emit, "complete", 100, f"Mapping complete: {found_count} found, {missing_count} missing candidates.", {
            "found_count": found_count,
            "missing_count": missing_count,
            "part_errors": mapping.part_errors,
        })

        return {"mapping": mapping}
