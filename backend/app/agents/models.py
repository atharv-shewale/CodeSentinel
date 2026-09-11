"""
CodeSentinel Agents Module: Models and Schemas.

Defines schemas for agent types, ask requests, grounded responses, and execution state.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """The 6 AI Agent Personas in CodeSentinel Module 3."""
    REQUIREMENT_AGENT = "REQUIREMENT_AGENT"
    CODE_AGENT = "CODE_AGENT"
    QA_TEST_AGENT = "QA_TEST_AGENT"
    AUDIT_AGENT = "AUDIT_AGENT"
    FAILURE_AGENT = "FAILURE_AGENT"
    ENGINEERING_INTELLIGENCE_AGENT = "ENGINEERING_INTELLIGENCE_AGENT"


class AgentAskRequest(BaseModel):
    question: str = Field(..., description="Natural language engineering question.")
    agent_type: Optional[AgentType] = Field(
        default=None,
        description="Optional agent specialization hint (if omitted, routed via Engineering Intelligence Agent)."
    )
    top_k: int = Field(default=5, ge=1, le=20, description="RAG retrieval depth.")


class AgentAskResponse(BaseModel):
    project_id: str
    question: str
    agent_type: AgentType
    response: str
    is_grounded: bool
    ungrounded_reason: Optional[str] = None
    cited_evidence: List[str] = Field(
        default_factory=list,
        description="List of verified citations (file paths, function qualified names, requirement IDs) found in answer."
    )
    retrieved_citations_pool: List[str] = Field(
        default_factory=list,
        description="All verifiable citation candidate tokens retrieved by RAG for this query."
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
