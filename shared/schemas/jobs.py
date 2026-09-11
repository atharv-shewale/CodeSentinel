"""
CodeSentinel Shared Schemas: Background Job Contracts.

Defines schemas for asynchronous background jobs managed across FastAPI,
Redis task queues, and worker execution units.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import utc_now


class JobState(str, Enum):
    """Execution lifecycle state of a background job."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    """Categorization of background tasks."""
    REPO_INGESTION = "REPO_INGESTION"
    REQUIREMENTS_PARSING = "REQUIREMENTS_PARSING"
    REQUIREMENT_PARSING = "REQUIREMENTS_PARSING"
    AST_ANALYSIS = "AST_ANALYSIS"
    KNOWLEDGE_GRAPH_BUILD = "KNOWLEDGE_GRAPH_BUILD"
    EMBEDDING_INDEXING = "EMBEDDING_INDEXING"
    TEST_GENERATION = "TEST_GENERATION"
    SANDBOX_EXECUTION = "SANDBOX_EXECUTION"
    COMPLIANCE_AUDIT = "COMPLIANCE_AUDIT"
    FAILURE_TRIAGE = "FAILURE_TRIAGE"
    REPORT_GENERATION = "REPORT_GENERATION"
    MUTATION_TESTING = "MUTATION_TESTING"


class JobProgress(BaseModel):
    """Real-time progress telemetry for a running background job."""
    model_config = ConfigDict(extra="forbid")

    current_step: int = Field(0, ge=0, description="Current step index.")
    total_steps: int = Field(100, ge=1, description="Total expected steps.")
    percentage: float = Field(0.0, ge=0.0, le=100.0, description="Calculated percentage complete (0.0 - 100.0).")
    status_message: str = Field("Initializing...", description="Current human-readable activity description.")


class JobStatus(BaseModel):
    """
    Background job status response payload.

    Returned by `GET /api/v1/jobs/{job_id}` to provide unified telemetry across all async operations.
    """
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., description="Unique job identifier string.")
    job_type: JobType = Field(..., description="Category of background job.")
    status: JobState = Field(default=JobState.PENDING, description="Current lifecycle state.")
    progress: JobProgress = Field(default_factory=JobProgress, description="Progress percentage and step metadata.")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Output payload upon successful completion.")
    error: Optional[str] = Field(default=None, description="Error message if job failed.")
    created_at: datetime = Field(default_factory=utc_now, description="Timestamp job was enqueued (UTC).")
    updated_at: datetime = Field(default_factory=utc_now, description="Timestamp job status was last updated (UTC).")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp job reached terminal state (UTC).")
