"""
CodeSentinel Shared Schemas: Common & Envelope Definitions.

This module defines common primitives, error structures, pagination metadata,
and the universal API response envelope (APIResponse[T]) enforced across all modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field
import uuid


def utc_now() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


class SortOrder(str, Enum):
    """Sort direction enumeration."""
    ASC = "asc"
    DESC = "desc"


class BaseEntity(BaseModel):
    """Base schema for all domain entities containing standard tracking metadata."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier (UUIDv4) for the entity."
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the entity was created (UTC)."
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the entity was last updated (UTC)."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata associated with the entity."
    )


class PaginationMeta(BaseModel):
    """Pagination metadata included in list responses."""
    model_config = ConfigDict(extra="forbid")

    total: int = Field(..., ge=0, description="Total number of items matching query.")
    page: int = Field(1, ge=1, description="Current page number (1-indexed).")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page.")
    total_pages: int = Field(..., ge=0, description="Total number of available pages.")
    has_next: bool = Field(False, description="Flag indicating if a next page exists.")
    has_prev: bool = Field(False, description="Flag indicating if a previous page exists.")


class APIError(BaseModel):
    """Structured error payload in the response envelope."""
    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'RESOURCE_NOT_FOUND', 'VALIDATION_ERROR')."
    )
    message: str = Field(
        ...,
        description="Human-readable error description."
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional diagnostic details or validation error breakdowns."
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Correlation / trace ID for debugging and log aggregation."
    )


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """
    Universal API Response Envelope.

    All endpoints across CodeSentinel MUST return responses formatted using this envelope.
    Ensures uniform client handling for success states, errors, data payloads, and metadata.
    """
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(
        ...,
        description="Indicates whether the request was completed successfully."
    )
    message: str = Field(
        default="Operation completed successfully.",
        description="Summary message about the operation result."
    )
    data: Optional[T] = Field(
        default=None,
        description="Typed data payload for successful responses. Null if error or empty."
    )
    error: Optional[APIError] = Field(
        default=None,
        description="Error details payload if success is False. Null for successful operations."
    )
    pagination: Optional[PaginationMeta] = Field(
        default=None,
        description="Pagination metadata for list endpoints."
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="Server response timestamp in UTC."
    )
