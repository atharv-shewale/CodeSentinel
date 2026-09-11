"""
CodeSentinel Shared Schemas: Failure & RCA Contract.

Defines schemas for recorded software anomalies, execution test failures,
runtime exceptions, regression alerts, and automated root cause analyses (RCA).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class FailureSeverity(str, Enum):
    """Severity classification of a detected failure."""
    BLOCKER = "BLOCKER"
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    TRIVIAL = "TRIVIAL"


class FailureCategory(str, Enum):
    """Categorization of failure root causes."""
    SYNTAX_ERROR = "SYNTAX_ERROR"
    LOGIC_ERROR = "LOGIC_ERROR"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    ASSERTION_FAILED = "ASSERTION_FAILED"
    TIMEOUT = "TIMEOUT"
    NULL_POINTER_OR_NONE = "NULL_POINTER_OR_NONE"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"
    PERFORMANCE_REGRESSION = "PERFORMANCE_REGRESSION"
    UNKNOWN = "UNKNOWN"


class FailureStatus(str, Enum):
    """Status of failure resolution."""
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    FIX_PROPOSED = "FIX_PROPOSED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class RootCauseAnalysis(BaseModel):
    """AI-generated or verified root cause diagnostic explanation."""
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="High-level explanation of the root failure cause.")
    suspected_entity_id: Optional[uuid.UUID] = Field(default=None, description="UUID of CodeEntity responsible for fault.")
    file_path: Optional[str] = Field(default=None, description="Suspected file path where defect originates.")
    line_number: Optional[int] = Field(default=None, ge=1, description="Suspected line number.")
    explanation: str = Field(..., description="Detailed technical mechanism of the defect.")
    suggested_fix: Optional[str] = Field(default=None, description="Proposed code diff or fix strategy.")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in RCA accuracy.")


class FailureBase(BaseModel):
    """Base schema for Failure attributes."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    test_execution_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of test execution run where failure occurred."
    )
    test_case_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of failing test case."
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Brief summary of failure."
    )
    error_message: str = Field(
        ...,
        description="Exception or failure message string."
    )
    stack_trace: Optional[str] = Field(
        default=None,
        description="Full runtime stack trace."
    )
    category: FailureCategory = Field(
        default=FailureCategory.UNKNOWN,
        description="Categorization of failure type."
    )
    severity: FailureSeverity = Field(
        default=FailureSeverity.MAJOR,
        description="Impact severity rating."
    )


class FailureCreate(FailureBase):
    """Payload to log a new failure."""
    pass


class FailureUpdate(BaseModel):
    """Payload to update failure status or assign RCA."""
    model_config = ConfigDict(extra="forbid")

    status: Optional[FailureStatus] = Field(default=None)
    severity: Optional[FailureSeverity] = Field(default=None)
    category: Optional[FailureCategory] = Field(default=None)
    root_cause: Optional[RootCauseAnalysis] = Field(default=None)


class Failure(FailureBase, BaseEntity):
    """
    Failure domain entity contract.

    Aggregates defects, automated triages, diagnostic traces, and AI repair recommendations.
    """
    status: FailureStatus = Field(
        default=FailureStatus.DETECTED,
        description="Current remediation status."
    )
    root_cause: Optional[RootCauseAnalysis] = Field(
        default=None,
        description="Automated or reviewed Root Cause Analysis payload."
    )
    occurrences_count: int = Field(
        default=1,
        ge=1,
        description="Number of times this distinct failure pattern has repeated."
    )
