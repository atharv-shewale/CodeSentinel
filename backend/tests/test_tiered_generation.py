"""
CodeSentinel Module 4 Tests: Tiered Test Generation Compliance (Tests 1-7).

Verifies:
1. REQUIREMENT_VERIFIED: generates 1 test per acceptance criterion (3 criteria -> 3 tests).
2. REQUIREMENT_VERIFIED: generates 0 tests for empty criteria (must be strictly 0).
3. SCHEMA_DERIVED: generates tests deterministically with 0 LLM calls.
4. COVERAGE_ONLY: labeled path execution only, asserts no correctness claims.
5. AI_INFERRED: carries needs_review=True in metadata and tag.
6. Duplicate rejection: structural deduplication rejects identical duplicate tests.
7. Invalid reference rejection: test referencing non-existent entity/route is discarded.
"""

import pytest
import uuid
from typing import Any, Dict
from unittest.mock import AsyncMock

from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from app.testing.generator import (
    AIInferredGenerator,
    CoverageOnlyGenerator,
    EntityExistenceValidator,
    RequirementVerifiedGenerator,
    SchemaDerivedGenerator,
    TestDeduplicator,
    TieredTestGenerator,
)

# Prevent pytest from attempting to collect imported schema classes as test suites
TestCase.__test__ = False
TestProvenance.__test__ = False
TestStatus.__test__ = False
TestType.__test__ = False


@pytest.mark.asyncio
async def test_requirement_verified_three_criteria():
    """Test 1: REQUIREMENT_VERIFIED generates exactly 1 test per acceptance criterion (3 criteria -> 3 tests)."""
    project_id = uuid.uuid4()
    req_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    system_model = {
        "requirements": [
            {
                "id": str(req_id),
                "identifier": "REQ-AUTH-01",
                "title": "User Authentication",
                "acceptance_criteria": [
                    "User provides valid email and password and receives 200 OK with JWT token.",
                    "User provides invalid password and receives 401 Unauthorized.",
                    "User provides malformed email and receives 422 Unprocessable Entity.",
                ],
                "target_entity_ids": [str(entity_id)],
            }
        ],
        "entities": [{"id": str(entity_id), "name": "authenticate_user"}],
        "routes": [],
    }

    mock_client = AsyncMock()
    mock_client.get_system_model.return_value = system_model
    mock_store = AsyncMock()
    mock_store.save_many.side_effect = lambda tests: tests

    generator = TieredTestGenerator(external_client=mock_client, store=mock_store)
    tests, stats = await generator.generate_for_project(
        project_id=project_id,
        tiers=[TestProvenance.REQUIREMENT_VERIFIED],
        system_model=system_model,
    )

    assert len(tests) == 3, f"Expected exactly 3 tests for 3 criteria, got {len(tests)}"
    for tc in tests:
        assert tc.provenance == TestProvenance.REQUIREMENT_VERIFIED
        assert tc.requirement_id == req_id
        assert "requirement_verified" in tc.tags
        assert len(tc.assertions) >= 1


@pytest.mark.asyncio
async def test_requirement_verified_empty_criteria():
    """Test 2: REQUIREMENT_VERIFIED generates strictly 0 tests for empty acceptance criteria."""
    project_id = uuid.uuid4()
    req_id = uuid.uuid4()

    system_model = {
        "requirements": [
            {
                "id": str(req_id),
                "identifier": "REQ-EMPTY-01",
                "title": "Empty Requirements Without Criteria",
                "acceptance_criteria": [],  # Strictly empty criteria
            }
        ],
        "entities": [],
        "routes": [],
    }

    mock_client = AsyncMock()
    mock_client.get_system_model.return_value = system_model
    mock_store = AsyncMock()
    mock_store.save_many.side_effect = lambda tests: tests

    generator = TieredTestGenerator(external_client=mock_client, store=mock_store)
    tests, stats = await generator.generate_for_project(
        project_id=project_id,
        tiers=[TestProvenance.REQUIREMENT_VERIFIED],
        system_model=system_model,
    )

    assert len(tests) == 0, f"Expected strictly 0 tests for empty criteria, got {len(tests)}"


@pytest.mark.asyncio
async def test_schema_derived_zero_llm_calls():
    """Test 3: SCHEMA_DERIVED generates tests deterministically with strictly 0 LLM calls."""
    project_id = uuid.uuid4()
    route_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    system_model = {
        "routes": [
            {
                "id": str(route_id),
                "path": "/api/v1/users",
                "method": "POST",
                "request_schema": {
                    "type": "object",
                    "properties": {"username": {"type": "string"}, "email": {"type": "string"}},
                    "required": ["username", "email"],
                },
                "response_schema": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "username": {"type": "string"}},
                },
            },
            {
                "id": str(uuid.uuid4()),
                "path": "/api/v1/items",
                "method": "GET",
                "request_schema": None,
                "response_schema": {"type": "array"},
            },
        ],
        "entities": [
            {
                "id": str(entity_id),
                "name": "calculate_hash",
                "entity_type": "FUNCTION",
                "parameters": [{"name": "salt", "type": "str"}],
            }
        ],
        "requirements": [],
    }

    mock_client = AsyncMock()
    mock_client.ask_agent.side_effect = AssertionError("LLM call must NOT be made for SCHEMA_DERIVED tier!")
    mock_store = AsyncMock()
    mock_store.save_many.side_effect = lambda tests: tests

    generator = TieredTestGenerator(external_client=mock_client, store=mock_store)
    tests, stats = await generator.generate_for_project(
        project_id=project_id,
        tiers=[TestProvenance.SCHEMA_DERIVED],
        system_model=system_model,
    )

    assert generator.schema_generator.llm_calls_made == 0, "Expected 0 LLM calls for schema derived tier!"
    assert len(tests) >= 2, "Expected schema-derived tests for routes and entities"
    for tc in tests:
        assert tc.provenance == TestProvenance.SCHEMA_DERIVED
        assert "schema_derived" in tc.tags
        assert tc.test_type in (TestType.API_CONTRACT, TestType.UNIT)


@pytest.mark.asyncio
async def test_coverage_only_labeled_path_execution_only():
    """Test 4: COVERAGE_ONLY labeled path execution only, asserts no correctness claims."""
    project_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    system_model = {
        "entities": [
            {
                "id": str(entity_id),
                "name": "process_pipeline_data",
                "file_path": "services/pipeline.py",
                "cyclomatic_complexity": 8,
            }
        ],
        "requirements": [],
        "routes": [],
    }

    mock_client = AsyncMock()
    mock_store = AsyncMock()
    mock_store.save_many.side_effect = lambda tests: tests

    generator = TieredTestGenerator(external_client=mock_client, store=mock_store)
    tests, stats = await generator.generate_for_project(
        project_id=project_id,
        tiers=[TestProvenance.COVERAGE_ONLY],
        system_model=system_model,
    )

    assert len(tests) == 1
    tc = tests[0]
    assert tc.provenance == TestProvenance.COVERAGE_ONLY
    assert tc.metadata.get("path_only_verification") is True
    assert tc.metadata.get("correctness_claim") is False
    assert "coverage_only" in tc.tags
    assert "path_only" in tc.tags


@pytest.mark.asyncio
async def test_ai_inferred_needs_review_metadata_and_tag():
    """Test 5: AI_INFERRED carries needs_review=True in metadata and tag."""
    project_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    system_model = {
        "entities": [
            {
                "id": str(entity_id),
                "name": "compute_financial_margin",
                "file_path": "finance/margin.py",
                "code": "def compute_financial_margin(revenue, cost): return revenue - cost",
            }
        ],
        "requirements": [],
        "routes": [],
    }

    mock_client = AsyncMock()
    mock_client.ask_agent.return_value = {
        "tests": [
            {
                "name": "test_compute_financial_margin_boundary",
                "description": "Verify boundary conditions for zero and negative revenue",
                "test_code": "def test_compute_financial_margin_boundary(): assert True",
                "assertions": [{"assertion_type": "EQUALS", "expected": True, "actual_target": "result"}],
            }
        ]
    }
    mock_store = AsyncMock()
    mock_store.save_many.side_effect = lambda tests: tests

    generator = TieredTestGenerator(external_client=mock_client, store=mock_store)
    tests, stats = await generator.generate_for_project(
        project_id=project_id,
        tiers=[TestProvenance.AI_INFERRED],
        system_model=system_model,
    )

    assert len(tests) == 1
    tc = tests[0]
    assert tc.provenance == TestProvenance.AI_INFERRED
    assert tc.metadata.get("needs_review") is True
    assert "needs_review" in tc.tags
    assert "ai_inferred" in tc.tags


def test_structural_deduplication():
    """Test 6: Duplicate rejection - structural deduplication rejects identical duplicate tests."""
    project_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    test1 = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_order_creation",
        description="Verify order creation",
        test_type=TestType.UNIT,
        provenance=TestProvenance.REQUIREMENT_VERIFIED,
        file_path="tests/test_order.py",
        test_code="def test_order_creation():\n    assert create_order({'id': 1}) is not None",
        target_entity_id=entity_id,
        status=TestStatus.ACTIVE,
    )

    # test2 has identical structural content (code and target entity) but different UUID and name
    test2 = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_order_creation_clone",
        description="Verify order creation clone",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/test_order.py",
        test_code="def test_order_creation():\n    assert create_order({'id': 1}) is not None",
        target_entity_id=entity_id,
        status=TestStatus.ACTIVE,
    )

    unique_tests, rejected = TestDeduplicator.filter_duplicates([test1, test2], existing_fingerprints=set())

    assert len(unique_tests) == 1, f"Expected 1 unique test after deduplication, got {len(unique_tests)}"
    assert rejected == 1
    assert unique_tests[0].id == test1.id


def test_entity_existence_validation():
    """Test 7: Invalid reference rejection - test referencing non-existent entity is discarded."""
    project_id = uuid.uuid4()
    valid_entity_id = uuid.uuid4()
    ghost_entity_id = uuid.uuid4()

    system_model = {
        "entities": [{"id": str(valid_entity_id), "name": "valid_function"}],
        "routes": [],
        "requirements": [],
    }

    valid_test = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_valid_entity",
        description="Valid test referencing real entity",
        test_type=TestType.UNIT,
        provenance=TestProvenance.SCHEMA_DERIVED,
        file_path="tests/test_valid.py",
        test_code="def test_valid_entity(): pass",
        target_entity_id=valid_entity_id,
        status=TestStatus.ACTIVE,
    )

    invalid_test = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_ghost_entity",
        description="Invalid test referencing non-existent entity",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/test_ghost.py",
        test_code="def test_ghost_entity(): pass",
        target_entity_id=ghost_entity_id,  # Non-existent in system_model!
        status=TestStatus.ACTIVE,
    )

    valid_tests, invalid_tests = EntityExistenceValidator.validate([valid_test, invalid_test], system_model)

    assert len(valid_tests) == 1, f"Expected only 1 valid test, got {len(valid_tests)}"
    assert len(invalid_tests) == 1, f"Expected 1 invalid test rejected, got {len(invalid_tests)}"
    assert valid_tests[0].id == valid_test.id
    assert invalid_tests[0].id == invalid_test.id
