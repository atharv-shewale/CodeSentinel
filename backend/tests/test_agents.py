"""
Unit & Integration Tests for Module 3 Part C: LLM Gateway + AI Agents.

Covers:
7. Strong Matching Context Query -> assert response includes at least 1 citation and is_grounded == True.
8. No Matching Context Query -> assert response is flagged 'ungrounded' (is_grounded == False).
9. LLM Gateway Swap Test -> assert agents call the gateway's interface, not a provider SDK directly.
10. LLM Provider Timeout/Failure -> assert typed LLMProviderError + bounded retry behavior.
"""

import inspect
import pytest
import uuid

from app.agents.agent_implementations import (
    AuditAgent,
    CodeAgent,
    EngineeringIntelligenceAgent,
    FailureAgent,
    QATestAgent,
    RequirementAgent,
)
from app.agents.gateway import (
    BaseLLMProvider,
    LLMGateway,
    LLMProviderError,
    MockLLMProvider,
    llm_gateway,
)
from app.agents.models import AgentType
from app.agents.service import AgentService
from app.knowledge_graph.service import KnowledgeGraphService
from app.rag.service import RAGService
from tests.fixtures.knowledge.sample_system_models import (
    PROJECT_A_ID,
    SAMPLE_SYSTEM_MODEL_PROJECT_A,
)


@pytest.mark.asyncio
class TestAIAgentsAndGateway:
    """Test Suite for LLM Gateway, Specialized Agents, and Grounding Invariants."""

    @pytest.fixture(autouse=True)
    async def setup_fixture(self):
        """Prepare knowledge graph and vector indices for Project A before each test."""
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )
        await RAGService.index_project_content(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )
        # Ensure mock provider is active with realistic synthesis
        llm_gateway.set_provider(MockLLMProvider())

    async def test_07_strong_matching_context_query_is_grounded_with_citations(self):
        """
        7. Strong Matching Context Test:
        A query with strong matching context -> assert the response includes at least
        one real citation to the retrieved evidence and is_grounded is True.
        """
        response = await AgentService.ask(
            project_id=PROJECT_A_ID,
            question="Explain how authenticate_user implements REQ-AUTH-001 in auth_service.py",
            agent_type=AgentType.CODE_AGENT,
        )

        assert response.is_grounded is True, f"Response should be grounded but was ungrounded: {response.ungrounded_reason}"
        assert len(response.cited_evidence) >= 1
        assert response.ungrounded_reason is None

        # Verify citation matches real retrieved entity symbols
        cited_set = set(response.cited_evidence)
        assert any(
            "auth_service.py" in c or "authenticate_user" in c or "REQ-AUTH-001" in c
            for c in cited_set
        )

    async def test_08_no_matching_context_query_flagged_ungrounded(self):
        """
        8. Ungrounded Fallback Test:
        A query with no matching context at all (e.g. asking about something completely
        non-existent) -> assert the response is flagged 'ungrounded', not silently answered.
        """
        non_existent_project = str(uuid.uuid4())

        response = await AgentService.ask(
            project_id=non_existent_project,
            question="How does the quantum blockchain teleportation module work?",
            agent_type=AgentType.REQUIREMENT_AGENT,
        )

        assert response.is_grounded is False
        assert response.ungrounded_reason is not None
        assert "could not locate" in response.response.lower() or "zero" in response.ungrounded_reason.lower() or "no" in response.ungrounded_reason.lower()
        assert len(response.cited_evidence) == 0

    async def test_09_llm_gateway_swap_and_agent_interface_compliance(self):
        """
        9. LLM Gateway Swap Test:
        Assert agents call the gateway's interface and never import or invoke provider SDKs directly.
        """
        # 1. Custom Provider Implementation
        class CustomTelemetryProvider(BaseLLMProvider):
            def __init__(self):
                self.calls = []

            async def generate_response(self, prompt: str, context: str = None, system_message: str = None) -> str:
                self.calls.append({"prompt": prompt, "context": context, "system": system_message})
                return "CustomTelemetryProvider response citing app/services/auth_service.py and REQ-AUTH-001"

        custom_provider = CustomTelemetryProvider()
        original_provider = llm_gateway.current_provider

        try:
            # Swap provider in gateway
            llm_gateway.set_provider(custom_provider)

            response = await AgentService.ask(
                project_id=PROJECT_A_ID,
                question="What requirements exist for authentication in auth_service.py?",
                agent_type=AgentType.REQUIREMENT_AGENT,
            )

            # Assert custom provider was invoked through gateway
            assert len(custom_provider.calls) == 1
            assert response.is_grounded is True
            assert any("auth_service.py" in c or "REQ-AUTH-001" in c for c in response.cited_evidence)

        finally:
            llm_gateway.set_provider(original_provider)

        # 2. Structural Inspection: Verify no agent module directly imports groq/openai SDKs
        from app.agents import agent_implementations, service, grounding

        for mod in [agent_implementations, service, grounding]:
            source_lines = inspect.getsource(mod)
            assert "import groq" not in source_lines, f"Direct groq import detected in {mod.__name__}"
            assert "from groq" not in source_lines, f"Direct groq import detected in {mod.__name__}"
            assert "import openai" not in source_lines, f"Direct openai import detected in {mod.__name__}"
            assert "from openai" not in source_lines, f"Direct openai import detected in {mod.__name__}"

    async def test_10_llm_provider_timeout_and_bounded_retry_behavior(self):
        """
        10. Error Handling & Retry Test:
        Assert that when an LLM provider times out or fails, bounded retries (max 2)
        are attempted before raising a typed LLMProviderError.
        """
        failing_provider = MockLLMProvider(fail_after_retries=True)
        original_provider = llm_gateway.current_provider

        try:
            llm_gateway.set_provider(failing_provider)

            with pytest.raises(LLMProviderError) as exc_info:
                await llm_gateway.generate(
                    prompt="Test prompt that should trigger retry failure",
                    context="Some context"
                )

            err = exc_info.value
            assert err.retries == 2
            assert "timeout/failure" in str(err).lower() or "retries" in str(err).lower()
            assert failing_provider.call_count >= 1

        finally:
            llm_gateway.set_provider(original_provider)
