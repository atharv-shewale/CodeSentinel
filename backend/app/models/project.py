"""
CodeSentinel Models: Project Database Model.

Persists validated Project domain entities into PostgreSQL as JSON/JSONB
alongside indexed identifier and timestamp columns.
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, String
from sqlalchemy.types import JSON
from .base import Base


class ProjectModel(Base):
    """PostgreSQL relational persistence model for Project records."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    name = Column(String(128), nullable=False, index=True)
    repository_url = Column(String(512), nullable=False)
    default_branch = Column(String(64), nullable=False, default="main")
    provider = Column(String(32), nullable=False, default="GITHUB")
    status = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    total_files = Column(String(32), default="0")
    total_lines_of_code = Column(String(32), default="0")

    # Complete validated Project object stored as JSONB / JSON
    data = Column(JSON, nullable=False)
