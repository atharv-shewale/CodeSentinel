"""
CodeSentinel Module 4 Tests: Failure Analysis Correlation & Grounding (Tests 17-18).

Verifies:
17. Failure correlation: Correlates failing execution with target function in system model,
    queries Module 3 failure_functions graph, and captures commit info without fabrication.
18. Grounding verification:
    - If is_grounded == True, populates RootCauseAnalysis narrative.
    - If is_grounded == False, OMITS speculative narrative and stores ungrounded evidence.
"""

import pytest
import uuid
from unittest.mock import AsyncMock

from shared.schemas.failure import FailureCategory, FailureSeverity, FailureStatus
from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from shared.schemas.test_execution import ExecutionStatus, TestResultItem
from app.failures.analyzer import FailureAnalyzer

# Prevent pytest from attempting to collect imported schema classes as test suites
TestCase.__test__ = False
TestProvenance.__test__ = False
TestStatus.__test__ = False
TestType.__test__ = False
TestResultItem.__test__ = False


@pytest.mark.asyncio
async def test_failure_correlation_with_target_function_and_commits():
    """Test 17: Correlates failure with target entity, commit SHA, and Module 3 failure_functions graph."""
    project_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    tc_id = uuid.uuid4()
    commit_sha = "f4c9a8b172e391"

    system_model = {
        "entities": [
            {
                "id": str(entity_id),
                "name": "verify_token_signature",
                "file_path": "auth/tokens.py",
                "start_line": 42,
            }
        ],
        "requirements": [],
        "routes": [],
    }

    test_case = TestCase(
        id=tc_id,
        project_id=project_id,
        name="test_verify_token_signature",
        description="Verify token signature implementation",
        test_type=TestType.UNIT,
        provenance=TestProvenance.REQUIREMENT_VERIFIED,
        file_path="tests/test_tokens.py",
        test_code="def test_verify_token_signature(): pass",
        target_entity_id=entity_id,
        status=TestStatus.ACTIVE,
    )

    result_item = TestResultItem(
        test_case_id=tc_id,
        test_name="test_verify_token_signature",
        status=ExecutionStatus.FAILED,
        duration_ms=45.0,
        error_message="AssertionError: Token signature mismatch",
        stack_trace="File 'auth/tokens.py', line 42, in verify_token_signature\n  assert computed == expected",
    )

    mock_client = AsyncMock()
    mock_client.get_system_model.return_value = system_model
    mock_client.query_knowledge_graph.return_value = [{"prior_failure_id": "prev-123"}]
    mock_client.ask_agent.return_value = {
        "is_grounded": True,
        "summary": "Key derivation parameter mismatch in HMAC algorithm",
        "explanation": "Salt parameter was omitted in the new cryptographic token format.",
        "suggested_fix": "+ salt=secret_salt",
        "confidence_score": 0.95,
    }
    mock_client.trigger_knowledge_graph_build.return_value = True

    mock_store = AsyncMock()
    mock_store.save.side_effect = lambda f: f

    analyzer = FailureAnalyzer(external_client=mock_client, store=mock_store)
    failure = await analyzer.analyze_failure(
        project_id=project_id,
        result_item=result_item,
        test_case=test_case,
        commit_sha=commit_sha,
    )

    assert failure.project_id == project_id
    assert failure.category == FailureCategory.ASSERTION_FAILED
    assert failure.severity == FailureSeverity.MAJOR
    assert failure.metadata["suspected_entity"] == "verify_token_signature"
    assert failure.metadata["commit_sha"] == commit_sha
    assert failure.metadata["graph_correlated"] is True

    # Verify Module 3 failure_functions graph query was made
    mock_client.query_knowledge_graph.assert_called_once_with(
        project_id=project_id,
        query_type="failure_functions",
        target_name="verify_token_signature",
    )


@pytest.mark.asyncio
async def test_grounding_verification_rule():
    """Test 18: Grounding verification - strictly accepts RCA if is_grounded=True, omits narrative if is_grounded=False."""
    project_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    system_model = {
        "entities": [{"id": str(entity_id), "name": "parse_payload"}],
    }

    result_item = TestResultItem(
        test_case_id=uuid.uuid4(),
        test_name="test_parse_payload",
        status=ExecutionStatus.FAILED,
        duration_ms=30.0,
        error_message="ValueError: Invalid header encoding",
        stack_trace="Traceback...",
    )

    mock_client = AsyncMock()
    mock_client.get_system_model.return_value = system_model
    mock_client.query_knowledge_graph.return_value = None
    mock_client.trigger_knowledge_graph_build.return_value = True

    mock_store = AsyncMock()
    mock_store.save.side_effect = lambda f: f

    analyzer = FailureAnalyzer(external_client=mock_client, store=mock_store)

    # CASE A: Grounded response (is_grounded == True)
    mock_client.ask_agent.return_value = {
        "is_grounded": True,
        "summary": "Encoding mismatch between UTF-8 and ASCII header parser",
        "explanation": "Parser expects UTF-8 but received Latin-1 byte payload.",
        "suggested_fix": "payload.decode('utf-8', errors='replace')",
        "confidence_score": 0.90,
    }

    grounded_failure = await analyzer.analyze_failure(
        project_id=project_id,
        result_item=result_item,
    )

    assert grounded_failure.root_cause is not None
    assert grounded_failure.root_cause.summary == "Encoding mismatch between UTF-8 and ASCII header parser"
    assert grounded_failure.status == FailureStatus.ROOT_CAUSE_IDENTIFIED
    assert grounded_failure.metadata["is_grounded"] is True

    # CASE B: Ungrounded response (is_grounded == False)
    # Grounding Rule: Must NOT accept speculative hallucination; omit narrative
    mock_client.ask_agent.return_value = {
        "is_grounded": False,  # Hallucinated / speculative
        "summary": "Maybe the database server had an intermittent network hiccup?",
        "explanation": "Speculative narrative not anchored in code evidence.",
    }

    ungrounded_failure = await analyzer.analyze_failure(
        project_id=project_id,
        result_item=result_item,
    )

    # Invariant: Speculative narrative is omitted!
    assert ungrounded_failure.root_cause is None, "RCA must be None when agent output is ungrounded!"
    assert ungrounded_failure.status == FailureStatus.DETECTED
    assert ungrounded_failure.metadata["is_grounded"] is False
