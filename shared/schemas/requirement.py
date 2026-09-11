"""
CodeSentinel Shared Schemas: Requirement Contract.

Defines schemas for software requirements, user stories, acceptance criteria,
and traceability linkages.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class RequirementType(str, Enum):
    """Categorization of requirements."""
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    API_CONTRACT = "API_CONTRACT"
    COMPLIANCE = "COMPLIANCE"


class RequirementPriority(str, Enum):
    """Priority levels for requirements engineering."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RequirementStatus(str, Enum):
    """Verification and implementation status of a requirement."""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    DEPRECATED = "DEPRECATED"


class RequirementBase(BaseModel):
    """Base schema for Requirement attributes."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    identifier: str = Field(
        ...,
        description="Business identifier (e.g. 'REQ-AUTH-001')."
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Short summary of the requirement."
    )
    description: str = Field(
        ...,
        description="Comprehensive specification and behavioral description."
    )
    req_type: RequirementType = Field(
        default=RequirementType.FUNCTIONAL,
        description="Category classification."
    )
    priority: RequirementPriority = Field(
        default=RequirementPriority.MEDIUM,
        description="Business or technical priority."
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of verifiable acceptance conditions."
    )
    linked_entity_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="UUIDs of code entities fulfilling or implementing this requirement."
    )


class RequirementCreate(RequirementBase):
    """Payload to create a new requirement."""
    pass


class RequirementUpdate(BaseModel):
    """Payload to update an existing requirement."""
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    description: Optional[str] = Field(default=None)
    req_type: Optional[RequirementType] = Field(default=None)
    priority: Optional[RequirementPriority] = Field(default=None)
    status: Optional[RequirementStatus] = Field(default=None)
    acceptance_criteria: Optional[List[str]] = Field(default=None)
    linked_entity_ids: Optional[List[uuid.UUID]] = Field(default=None)


class Requirement(RequirementBase, BaseEntity):
    """
    Requirement domain entity contract.

    Serves as the specification anchor for requirement-verified test cases and compliance audits.
    """
    status: RequirementStatus = Field(
        default=RequirementStatus.DRAFT,
        description="Verification lifecycle status."
    )
    verification_coverage_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Calculated automated test coverage percentage for this requirement."
    )
