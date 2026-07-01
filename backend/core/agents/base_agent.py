"""
core/agents/base_agent.py

Abstract base class for all agents in the Railway GCC Contract Analyzer.
Every agent has a name, a run() method, and an emit() hook for SSE events.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


logger = logging.getLogger(__name__)


@dataclass
class AgentEvent:
    """An SSE event emitted by an agent during execution."""
    agent: str
    status: str        # "started" | "running" | "complete" | "error"
    progress: int      # 0–100 percentage
    message: str       # Human-readable status message
    data: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents.

    Subclasses must implement:
        name (str): Human-readable agent name
        run(input, emit) -> output: Core execution logic
    """

    name: str = "BaseAgent"

    @abstractmethod
    def run(
        self,
        input_data: Any,
        emit: Optional[Callable[[AgentEvent], None]] = None,
    ) -> Any:
        """
        Execute the agent's task.

        Args:
            input_data: Input from the previous agent or the orchestrator.
            emit:       Optional callback to emit SSE events for real-time progress.

        Returns:
            Output data to pass to the next agent.
        """
        ...

    def _emit(
        self,
        emit: Optional[Callable[[AgentEvent], None]],
        status: str,
        progress: int,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Helper to emit an agent event if the emit callback is provided."""
        event = AgentEvent(
            agent=self.name,
            status=status,
            progress=progress,
            message=message,
            data=data or {},
        )
        logger.info("[%s] %s — %s", self.name, status, message)
        if emit:
            emit(event)
