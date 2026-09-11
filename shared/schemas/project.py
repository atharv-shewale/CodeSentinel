"""
CodeSentinel Shared Schemas: Project Contract.

Defines schemas for managing software projects, repository configurations,
and analysis lifecycle statuses.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
import uuid
from .common import BaseEntity


class ProjectStatus(str, Enum):
    """Lifecycle status of a project within CodeSentinel."""
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    INDEXING = "INDEXING"
    ANALYZING = "ANALYZING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class RepoProvider(str, Enum):
    """Supported Git repository hosting providers."""
    GITHUB = "GITHUB"
    GITLAB = "GITLAB"
    BITBUCKET = "BITBUCKET"
    LOCAL = "LOCAL"


class ProjectBase(BaseModel):
    """Base schema for Project attributes."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable project identifier."
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Comprehensive description of the target application."
    )
    repository_url: str = Field(
        ...,
        description="Git clone URL or local file path to the repository."
    )
    default_branch: str = Field(
        default="main",
        description="Default branch for indexing and continuous intelligence."
    )
    provider: RepoProvider = Field(
        default=RepoProvider.GITHUB,
        description="Git hosting platform provider."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Search and organization tags."
    )


class ProjectCreate(ProjectBase):
    """Request payload for initializing a new CodeSentinel project."""
    access_token: Optional[str] = Field(
        default=None,
        description="Optional Git provider access token for private repository cloning."
    )


class ProjectUpdate(BaseModel):
    """Payload for partial updates to an existing project."""
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1024)
    default_branch: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    status: Optional[ProjectStatus] = Field(default=None)


class Project(ProjectBase, BaseEntity):
    """
    Complete Project domain entity contract.

    Serves as the root container for all code intelligence, graph relations,
    requirements, tests, executions, and audits.
    """
    status: ProjectStatus = Field(
        default=ProjectStatus.INITIALIZING,
        description="Current processing/lifecycle state of the project."
    )
    last_indexed_commit: Optional[str] = Field(
        default=None,
        description="Full SHA-1 of the most recently indexed commit."
    )
    total_files: int = Field(
        default=0,
        ge=0,
        description="Total number of analyzed source files."
    )
    total_lines_of_code: int = Field(
        default=0,
        ge=0,
        description="Total lines of code (LOC) detected in the codebase."
    )
