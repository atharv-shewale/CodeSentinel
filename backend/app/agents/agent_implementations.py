"""
CodeSentinel Agents Module: Agent Implementations & LangGraph Workflow.

Contains the 5 specialized reasoning agents + 1 Engineering Intelligence Coordinator:
1. RequirementAgent: Answers questions and summarizes requirements using RAG context.
2. CodeAgent: Explains code structure, signatures, and behavior using RAG + graph context.
3. QATestAgent: Proposes test-relevant observations & highlights coverage gaps (no test generation).
4. AuditAgent: Interprets security and code smell findings.
5. FailureAgent: Correlates failures with related functions, commits, and graph traces.
6. EngineeringIntelligenceAgent: Synthesizes multi-agent reasoning into unified engineering intelligence.

All agents call the LLMGateway and NEVER call a provider SDK directly.
"""

from typing import Any, Dict, List, Optional
from app.agents.gateway import llm_gateway
from app.agents.models import AgentType
from app.agents.state import AgentState
from app.rag.models import RAGContext

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "__end__"


def format_context_for_agent(rag_context: RAGContext) -> str:
    """Helper to convert structured RAGContext into rich context string for prompts."""
    sections = []

    if rag_context.requirement_results:
        sections.append("### REQUIREMENTS:")
        for r in rag_context.requirement_results:
            sections.append(f"- [{r.metadata.get('identifier', 'REQ')}] {r.title}:\n  {r.content}")

    if rag_context.code_results:
        sections.append("### CODE ENTITIES:")
        for c in rag_context.code_results:
            sections.append(f"- [{c.file_path or 'code'}] {c.title}:\n  {c.content}")

    if rag_context.test_results:
        sections.append("### TESTS:")
        for t in rag_context.test_results:
            sections.append(f"- [{t.file_path or 'test'}] {t.title} (Provenance: {t.metadata.get('provenance', 'UNKNOWN')}):\n  {t.content}")

    if rag_context.finding_results:
        sections.append("### AUDIT FINDINGS:")
        for f in rag_context.finding_results:
            sections.append(f"- [{f.metadata.get('severity', 'FINDING')}] {f.title}:\n  {f.content}")

    # Graph traversals
    g_ctx = rag_context.graph_context
    if g_ctx.get("call_neighborhoods"):
        sections.append("### CALL GRAPH NEIGHBORHOODS:")
        for cn in g_ctx["call_neighborhoods"]:
            sections.append(
                f"- Function '{cn.get('target_function')}': Callers={cn.get('callers', [])}, Callees={cn.get('callees', [])}"
            )

    if g_ctx.get("untested_requirements"):
        sections.append("### UNTESTED REQUIREMENTS (GRAPH):")
        for ur in g_ctx["untested_requirements"]:
            sections.append(f"- {ur.get('identifier')}: {ur.get('title')} (Linked Functions: {ur.get('linked_functions', [])})")

    if g_ctx.get("failure_traces"):
        sections.append("### FAILURE TRACES (GRAPH):")
        for ft in g_ctx["failure_traces"]:
            sections.append(f"- Failure {ft.get('failure_id')}: {ft.get('failure_title')} -> Related: {ft.get('related_functions', [])}")

    return "\n\n".join(sections)


class RequirementAgent:
    """Answers questions about and summarizes requirements using RAG context."""

    SYSTEM_PROMPT = (
        "You are CodeSentinel Requirement Agent. Your role is to analyze, summarize, and clarify "
        "software requirements and specifications. Always cite specific Requirement IDs (e.g. REQ-AUTH-001) "
        "and linked file paths or function names from the retrieved context."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)
        prompt = (
            f"Please address the following requirements question based on the provided codebase context:\n"
            f"Question: {question}\n\n"
            f"Provide a clear, requirement-grounded analysis citing specific requirement identifiers."
        )
        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


class CodeAgent:
    """Explains code structure, call graphs, and behavior using RAG + graph context."""

    SYSTEM_PROMPT = (
        "You are CodeSentinel Code Agent. Your role is to explain code architecture, class structures, "
        "function logic, and call graph hierarchies. Always cite specific file paths and function qualified names."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)
        prompt = (
            f"Please analyze the codebase structure and behavior to answer:\n"
            f"Question: {question}\n\n"
            f"Provide an architectural explanation citing specific source files and function names."
        )
        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


class QATestAgent:
    """
    Proposes test-relevant observations (NOT test generation itself — Module 4's job).
    Reasons about testing gaps, untested requirements, and test provenance.
    """

    SYSTEM_PROMPT = (
        "You are CodeSentinel QA/Test Reasoning Agent. Your role is to reason about test coverage, "
        "test provenance (REQUIREMENT_VERIFIED vs COVERAGE_ONLY), and highlight untested requirements or functions. "
        "Do NOT generate full executable test code (that is handled downstream); provide analytical observations "
        "and cite specific test files, function names, or requirement identifiers."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)
        prompt = (
            f"Please evaluate the testing and verification posture for:\n"
            f"Question: {question}\n\n"
            f"Highlight untested requirements, coverage gaps, and test provenance observations citing specific artifacts."
        )
        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


class AuditAgent:
    """Interprets audit findings and security evidence in the graph/context."""

    SYSTEM_PROMPT = (
        "You are CodeSentinel Audit Agent. Your role is to interpret security findings, code smells, "
        "and architecture compliance evidence. Always cite rule IDs, affected files, and severity levels."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)
        prompt = (
            f"Please interpret the audit and security evidence for:\n"
            f"Question: {question}\n\n"
            f"Provide audit risk assessment citing specific rule IDs and file locations."
        )
        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


class FailureAgent:
    """Correlates defects and failures with related code, commits, and graph traces."""

    SYSTEM_PROMPT = (
        "You are CodeSentinel Failure Reasoning Agent. Your role is to correlate failures and exceptions "
        "with related code functions, executions, and recent commits. Always cite failure IDs and related functions."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)
        prompt = (
            f"Please analyze the failure correlation and root cause indicators for:\n"
            f"Question: {question}\n\n"
            f"Correlate the failure with related functions and commits, citing specific entity names."
        )
        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


class EngineeringIntelligenceAgent:
    """
    Master coordinator agent that can consult specialized agents and synthesize
    a unified engineering intelligence response.
    """

    SYSTEM_PROMPT = (
        "You are CodeSentinel Master Engineering Intelligence Agent. You synthesize insights from "
        "Requirements, Code Architecture, QA/Testing, Security Audits, and Failure Analysis into a "
        "comprehensive, executive-level technical answer. Always cite specific evidence from the codebase."
    )

    @classmethod
    async def run(cls, question: str, rag_context: RAGContext) -> str:
        ctx_text = format_context_for_agent(rag_context)

        # Consult specialized perspectives based on query signals
        sub_analyses = []
        q_lower = question.lower()

        if any(w in q_lower for w in ["req", "spec", "acceptance", "feature"]):
            req_out = await RequirementAgent.run(question, rag_context)
            sub_analyses.append(f"Requirement Analysis:\n{req_out}")

        if any(w in q_lower for w in ["code", "function", "class", "architecture", "call"]):
            code_out = await CodeAgent.run(question, rag_context)
            sub_analyses.append(f"Code Architecture Analysis:\n{code_out}")

        if any(w in q_lower for w in ["test", "coverage", "untested", "qa", "provenance"]):
            qa_out = await QATestAgent.run(question, rag_context)
            sub_analyses.append(f"QA & Testing Analysis:\n{qa_out}")

        if any(w in q_lower for w in ["audit", "security", "vuln", "smell", "compliance"]):
            audit_out = await AuditAgent.run(question, rag_context)
            sub_analyses.append(f"Security & Audit Analysis:\n{audit_out}")

        if any(w in q_lower for w in ["fail", "error", "crash", "bug", "exception"]):
            fail_out = await FailureAgent.run(question, rag_context)
            sub_analyses.append(f"Failure Correlation Analysis:\n{fail_out}")

        # If no specialized signals triggered, run Code and Requirement by default
        if not sub_analyses:
            code_out = await CodeAgent.run(question, rag_context)
            sub_analyses.append(f"Code Analysis:\n{code_out}")

        combined_sub = "\n\n".join(sub_analyses)

        prompt = (
            f"Synthesize a final unified engineering intelligence answer for:\n"
            f"User Question: {question}\n\n"
            f"Specialized Agent Findings:\n{combined_sub}\n\n"
            f"Please synthesize these findings into a unified, evidence-grounded response."
        )

        return await llm_gateway.generate(
            prompt=prompt,
            context=ctx_text,
            system_message=cls.SYSTEM_PROMPT
        )


def build_langgraph_workflow():
    """Builds a LangGraph StateGraph state machine for multi-agent dispatch."""
    if not LANGGRAPH_AVAILABLE or StateGraph is None:
        return None

    try:
        workflow = StateGraph(AgentState)

        async def route_node(state: AgentState) -> AgentState:
            return state

        async def requirement_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await RequirementAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        async def code_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await CodeAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        async def qa_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await QATestAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        async def audit_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await AuditAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        async def failure_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await FailureAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        async def engineering_intelligence_node(state: AgentState) -> AgentState:
            ctx = state.get("rag_context")
            resp = await EngineeringIntelligenceAgent.run(state["question"], ctx)
            state["final_response"] = resp
            return state

        workflow.add_node("router", route_node)
        workflow.add_node("requirement_agent", requirement_node)
        workflow.add_node("code_agent", code_node)
        workflow.add_node("qa_agent", qa_node)
        workflow.add_node("audit_agent", audit_node)
        workflow.add_node("failure_agent", failure_node)
        workflow.add_node("engineering_intelligence_agent", engineering_intelligence_node)

        workflow.set_entry_point("router")

        def route_condition(state: AgentState) -> str:
            target = state.get("target_agent_type")
            if target == AgentType.REQUIREMENT_AGENT.value:
                return "requirement_agent"
            elif target == AgentType.CODE_AGENT.value:
                return "code_agent"
            elif target == AgentType.QA_TEST_AGENT.value:
                return "qa_agent"
            elif target == AgentType.AUDIT_AGENT.value:
                return "audit_agent"
            elif target == AgentType.FAILURE_AGENT.value:
                return "failure_agent"
            return "engineering_intelligence_agent"

        workflow.add_conditional_edges("router", route_condition)
        workflow.add_edge("requirement_agent", END)
        workflow.add_edge("code_agent", END)
        workflow.add_edge("qa_agent", END)
        workflow.add_edge("audit_agent", END)
        workflow.add_edge("failure_agent", END)
        workflow.add_edge("engineering_intelligence_agent", END)

        return workflow.compile()
    except Exception:
        return None


# Compiled LangGraph Workflow
agent_graph_app = build_langgraph_workflow()
