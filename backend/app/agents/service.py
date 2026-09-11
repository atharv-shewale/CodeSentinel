"""
CodeSentinel Agents Module: Service Layer.

Coordinates:
1. Hybrid RAG retrieval for engineering questions.
2. Multi-agent routing and execution via LangGraph.
3. Post-processing Grounding Inspection to enforce empirical codebase citations.
"""

from typing import Any, Dict, List, Optional, Union
import uuid

from app.agents.agent_implementations import (
    AuditAgent,
    CodeAgent,
    EngineeringIntelligenceAgent,
    FailureAgent,
    QATestAgent,
    RequirementAgent,
    agent_graph_app,
)
from app.agents.grounding import GroundingInspector
from app.agents.models import AgentAskResponse, AgentType
from app.core.logging import logger
from app.rag.service import RAGService


class AgentService:
    """Service orchestrating AI Agent workflows, RAG grounding, and citation validation."""

    @classmethod
    async def ask(
        cls,
        project_id: Union[str, uuid.UUID],
        question: str,
        agent_type: Optional[AgentType] = None,
        top_k: int = 5,
    ) -> AgentAskResponse:
        """
        Processes a natural language question through the multi-agent AI core.
        Enforces RAG retrieval, agent generation, and mandatory grounding validation.
        """
        pid_str = str(project_id)
        selected_agent = agent_type or AgentType.ENGINEERING_INTELLIGENCE_AGENT

        logger.info(f"Agent ask request on project {pid_str} with agent {selected_agent.value}: '{question[:60]}'")

        # 1. Retrieve hybrid RAG Context (Vectors + Graph)
        rag_context = await RAGService.query_context(
            project_id=pid_str,
            query=question,
            top_k=top_k,
        )

        # 2. Check if any context exists at all
        if rag_context.total_hits == 0 and not rag_context.graph_context.get("call_neighborhoods") and not rag_context.graph_context.get("untested_requirements"):
            # Empty context -> Agent MUST flag ungrounded rather than fabricating
            ungrounded_msg = (
                f"I could not locate any relevant code, requirements, or graph artifacts in project {pid_str} "
                f"to answer the question: '{question}'. Please ensure the project content is indexed."
            )
            is_grounded, cited, reason = GroundingInspector.inspect(
                response_text=ungrounded_msg,
                rag_context=rag_context,
                project_id=pid_str,
                question=question
            )
            return AgentAskResponse(
                project_id=pid_str,
                question=question,
                agent_type=selected_agent,
                response=ungrounded_msg,
                is_grounded=False,
                ungrounded_reason=reason or "No codebase context retrieved for query.",
                cited_evidence=[],
                retrieved_citations_pool=[],
                metadata={"retrieval_hits": 0}
            )

        # 3. Execute Agent Workflow (via LangGraph or specialized agent class)
        raw_response = ""
        if agent_graph_app is not None:
            try:
                state_input = {
                    "project_id": pid_str,
                    "question": question,
                    "target_agent_type": selected_agent.value,
                    "rag_context": rag_context,
                    "intermediate_steps": [],
                }
                final_state = await agent_graph_app.ainvoke(state_input)
                raw_response = final_state.get("final_response", "")
            except Exception as e:
                logger.warning(f"LangGraph execution exception ({e}). Falling back to direct agent call.")

        if not raw_response:
            # Direct class execution fallback
            if selected_agent == AgentType.REQUIREMENT_AGENT:
                raw_response = await RequirementAgent.run(question, rag_context)
            elif selected_agent == AgentType.CODE_AGENT:
                raw_response = await CodeAgent.run(question, rag_context)
            elif selected_agent == AgentType.QA_TEST_AGENT:
                raw_response = await QATestAgent.run(question, rag_context)
            elif selected_agent == AgentType.AUDIT_AGENT:
                raw_response = await AuditAgent.run(question, rag_context)
            elif selected_agent == AgentType.FAILURE_AGENT:
                raw_response = await FailureAgent.run(question, rag_context)
            else:
                raw_response = await EngineeringIntelligenceAgent.run(question, rag_context)

        # 4. Mandatory Post-Processing Grounding Verification
        is_grounded, cited_evidence, ungrounded_reason = GroundingInspector.inspect(
            response_text=raw_response,
            rag_context=rag_context,
            project_id=pid_str,
            question=question
        )

        return AgentAskResponse(
            project_id=pid_str,
            question=question,
            agent_type=selected_agent,
            response=raw_response,
            is_grounded=is_grounded,
            ungrounded_reason=ungrounded_reason,
            cited_evidence=cited_evidence,
            retrieved_citations_pool=rag_context.evidence_citations,
            metadata={
                "total_vector_hits": rag_context.total_hits,
                "graph_neighborhood_count": len(rag_context.graph_context.get("call_neighborhoods", [])),
            }
        )
