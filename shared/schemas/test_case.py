"""
CodeSentinel Shared Schemas: TestCase Contract.

Defines schemas for generated and ingested test cases, assertions, target bindings,
and strictly tracks provenance lineage for downstream verification confidence.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class TestProvenance(str, Enum):
    """
    Mandatory Provenance Origin for Test Cases.

    Establishes trust, auditability, and execution priority across CodeSentinel:
    - REQUIREMENT_VERIFIED: Directly derived from and validated against approved Requirements / User Stories.
    - SCHEMA_DERIVED: Automatically generated from OpenAPI / JSON schemas / AST parameter signatures.
    - COVERAGE_ONLY: Generated to maximize structural AST branch / statement coverage without semantic specs.
    - AI_INFERRED: Inferred purely by LLM heuristics from code patterns, edge cases, and historical failures.
    """
    REQUIREMENT_VERIFIED = "REQUIREMENT_VERIFIED"
    SCHEMA_DERIVED = "SCHEMA_DERIVED"
    COVERAGE_ONLY = "COVERAGE_ONLY"
    AI_INFERRED = "AI_INFERRED"
    MUTATION_TARGETED = "MUTATION_TARGETED"


class TestType(str, Enum):
    """Execution category classification for test cases."""
    UNIT = "UNIT"
    INTEGRATION = "INTEGRATION"
    E2E = "E2E"
    PROPERTY_BASED = "PROPERTY_BASED"
    MUTATION = "MUTATION"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    API_CONTRACT = "API_CONTRACT"


class TestStatus(str, Enum):
    """Current evaluation status of the test definition."""
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    QUARANTINED = "QUARANTINED"
    DEPRECATED = "DEPRECATED"
    FLAKY = "FLAKY"


class AssertionSpec(BaseModel):
    """Structured assertion definition."""
    model_config = ConfigDict(extra="forbid")

    assertion_type: str = Field(..., description="Type of check (e.g., 'EQUALS', 'STATUS_CODE', 'EXCEPTION_RAISED', 'MATCHES_REGEX').")
    expected: Any = Field(..., description="Expected output, status, or expression.")
    actual_target: str = Field(..., description="Variable, path, or expression being evaluated.")
    description: Optional[str] = Field(default=None, description="Human description of what this assertion guarantees.")


class TestCaseBase(BaseModel):
    """Base schema for TestCase attributes."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Descriptive name of the test case."
    )
    description: str = Field(
        ...,
        description="Explanation of scenario, preconditions, inputs, and expected behavior."
    )
    test_type: TestType = Field(
        default=TestType.UNIT,
        description="Test execution category."
    )
    provenance: TestProvenance = Field(
        ...,
        description="Mandatory origin category proving how this test was synthesized and trusted."
    )
    target_entity_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of CodeEntity (function/class) being tested."
    )
    target_route_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of APIRoute being verified if contract test."
    )
    requirement_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of Requirement if provenance is REQUIREMENT_VERIFIED."
    )
    file_path: str = Field(
        ...,
        description="Target test suite file path (e.g. 'tests/unit/test_auth.py')."
    )
    test_code: str = Field(
        ...,
        description="Executable test implementation code."
    )
    setup_code: Optional[str] = Field(
        default=None,
        description="Setup fixtures, mocks, and environment preparation code."
    )
    teardown_code: Optional[str] = Field(
        default=None,
        description="Cleanup and resource disposal code."
    )
    assertions: List[AssertionSpec] = Field(
        default_factory=list,
        description="Structured list of assertions evaluated in this test."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for selective execution (e.g. 'smoke', 'slow', 'security')."
    )


class TestCaseCreate(TestCaseBase):
    """Payload to create a new test case."""
    pass


class TestCaseUpdate(BaseModel):
    """Payload to update an existing test case."""
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    description: Optional[str] = Field(default=None)
    status: Optional[TestStatus] = Field(default=None)
    test_code: Optional[str] = Field(default=None)
    setup_code: Optional[str] = Field(default=None)
    teardown_code: Optional[str] = Field(default=None)
    assertions: Optional[List[AssertionSpec]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class TestCase(TestCaseBase, BaseEntity):
    """
    TestCase domain entity contract.

    Represents an actionable test artifact, tracking execution history, stability,
    and formal provenance metadata.
    """
    status: TestStatus = Field(
        default=TestStatus.ACTIVE,
        description="Current operational lifecycle status."
    )
    execution_count: int = Field(
        default=0,
        ge=0,
        description="Total executions recorded."
    )
    pass_count: int = Field(
        default=0,
        ge=0,
        description="Total successful passes."
    )
    fail_count: int = Field(
        default=0,
        ge=0,
        description="Total recorded failures."
    )
    flakiness_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Calculated flakiness probability index between 0.0 (stable) and 1.0 (highly flaky)."
    )
