"""
CodeSentinel Shared Schemas: TestExecution Contract.

Defines schemas for test execution runs, sandbox container telemetry,
individual test results, code coverage, and performance benchmarks.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class ExecutionStatus(str, Enum):
    """Execution run status state."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class ExecutionEnvironment(str, Enum):
    """Sandbox environment type."""
    DOCKER_SANDBOX = "DOCKER_SANDBOX"
    LOCAL_PROCESS = "LOCAL_PROCESS"
    KUBERNETES_JOB = "KUBERNETES_JOB"


class TestResultItem(BaseModel):
    """Detailed result for an individual test case evaluation within a suite execution."""
    model_config = ConfigDict(extra="forbid")

    test_case_id: uuid.UUID = Field(..., description="UUID of the corresponding TestCase.")
    test_name: str = Field(..., description="Test name or test identifier string.")
    status: ExecutionStatus = Field(..., description="Result outcome.")
    duration_ms: float = Field(..., ge=0.0, description="Duration in milliseconds.")
    error_message: Optional[str] = Field(default=None, description="Exception message or assertion error if failed.")
    stack_trace: Optional[str] = Field(default=None, description="Full stack trace string if failed.")
    stdout: Optional[str] = Field(default=None, description="Captured standard output.")
    stderr: Optional[str] = Field(default=None, description="Captured standard error.")


class CoverageMetrics(BaseModel):
    """Coverage telemetry collected during execution."""
    model_config = ConfigDict(extra="forbid")

    statement_coverage_pct: float = Field(0.0, ge=0.0, le=100.0, description="Statement coverage percentage.")
    branch_coverage_pct: float = Field(0.0, ge=0.0, le=100.0, description="Branch coverage percentage.")
    line_coverage_pct: float = Field(0.0, ge=0.0, le=100.0, description="Line coverage percentage.")
    covered_lines: int = Field(0, ge=0, description="Number of covered source lines.")
    total_lines: int = Field(0, ge=0, description="Total executable source lines.")
    covered_files: List[str] = Field(default_factory=list, description="List of source file paths evaluated.")


class TestExecutionBase(BaseModel):
    """Base schema for TestExecution."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    triggered_by: str = Field(
        default="SYSTEM",
        description="User, agent, or CI trigger initiating execution (e.g. 'agent:test-generator', 'user:dev1')."
    )
    environment: ExecutionEnvironment = Field(
        default=ExecutionEnvironment.DOCKER_SANDBOX,
        description="Isolated execution runtime environment."
    )
    commit_sha: Optional[str] = Field(
        default=None,
        description="Git commit SHA executed against."
    )
    test_case_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="List of TestCase UUIDs targeted in this run."
    )


class TestExecutionCreate(TestExecutionBase):
    """Payload to trigger a test execution run."""
    pass


class TestExecution(TestExecutionBase, BaseEntity):
    """
    TestExecution domain entity contract.

    Stores audit trail of sandbox test runs, runtime logs, aggregate pass/fail counts,
    and coverage telemetry.
    """
    status: ExecutionStatus = Field(
        default=ExecutionStatus.QUEUED,
        description="Current execution lifecycle status."
    )
    total_tests: int = Field(default=0, ge=0, description="Total test count.")
    passed_tests: int = Field(default=0, ge=0, description="Passed test count.")
    failed_tests: int = Field(default=0, ge=0, description="Failed test count.")
    errored_tests: int = Field(default=0, ge=0, description="Errored/aborted test count.")
    total_duration_ms: float = Field(default=0.0, ge=0.0, description="Total run duration in milliseconds.")
    results: List[TestResultItem] = Field(
        default_factory=list,
        description="Itemized list of individual test results."
    )
    coverage: Optional[CoverageMetrics] = Field(
        default=None,
        description="Coverage measurements if collected."
    )
    sandbox_container_id: Optional[str] = Field(
        default=None,
        description="ID of isolated Docker sandbox container utilized."
    )
