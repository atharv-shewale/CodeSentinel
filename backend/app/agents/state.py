"""
CodeSentinel Agents Module: LangGraph State Definitions.

Defines the typed dictionary state shared across multi-agent nodes in LangGraph.
"""

from typing import Any, Dict, List, Optional, TypedDict
from app.rag.models import RAGContext


class AgentState(TypedDict, total=False):
    """LangGraph State Container."""
    project_id: str
    question: str
    target_agent_type: str
    rag_context: Optional[RAGContext]
    context_text: str
    intermediate_steps: List[Dict[str, Any]]
    agent_outputs: Dict[str, str]
    final_response: str
    citations: List[str]
    is_grounded: bool
    ungrounded_reason: Optional[str]
