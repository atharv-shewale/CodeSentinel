"""
CodeSentinel Ingestion Module: Request & Ingestion Schemas.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IngestionSourceType(str, Enum):
    """Supported source acquisition types."""
    GITHUB = "github"
    ZIP = "zip"
    LOCAL = "local"


class IngestRepoRequest(BaseModel):
    """
    Request payload for acquiring and profiling a codebase repository.

    Supports:
    - GitHub URL: {source_type: "github", source: "https://github.com/..."}
    - ZIP Reference: {source_type: "zip", file_id: "..."} or {source_type: "zip", zip_base64: "..."}
    - Phase 0 Compatible: {repository_url: "https://github.com/..."}
    """
    model_config = ConfigDict(extra="ignore")

    source_type: Optional[IngestionSourceType] = Field(
        default=None,
        description="Acquisition source type: 'github' or 'zip'."
    )
    source: Optional[str] = Field(
        default=None,
        description="Source identifier (e.g. GitHub URL or local path)."
    )
    repository_url: Optional[str] = Field(
        default=None,
        description="Direct Git repository clone URL (backward compatible with Phase 0)."
    )
    branch: Optional[str] = Field(
        default="main",
        description="Target git branch to clone."
    )
    access_token: Optional[str] = Field(
        default=None,
        description="Optional personal access token for private GitHub repositories."
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Reference identifier to an uploaded ZIP file."
    )
    zip_base64: Optional[str] = Field(
        default=None,
        description="Optional base64-encoded ZIP archive payload for direct inline submission."
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Optional human-readable project name override."
    )

    def get_effective_source_type(self) -> IngestionSourceType:
        """Determine normalized source type based on provided fields."""
        if self.source_type:
            return self.source_type
        if self.file_id or self.zip_base64:
            return IngestionSourceType.ZIP
        return IngestionSourceType.GITHUB

    def get_effective_url_or_source(self) -> str:
        """Extract the effective URL or source string."""
        if self.source:
            return self.source
        if self.repository_url:
            return self.repository_url
        if self.file_id:
            return f"zip://{self.file_id}"
        return ""
