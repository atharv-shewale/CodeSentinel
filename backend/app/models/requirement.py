"""
CodeSentinel Models: Requirement Database Model.

Persists validated Requirement domain entities extracted from specifications per project in PostgreSQL.
"""

from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.types import JSON
from .base import Base


class RequirementModel(Base):
    """PostgreSQL relational persistence model for Project Requirements."""
    __tablename__ = "requirements"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    project_id = Column(String(36), index=True, nullable=False)
    identifier = Column(String(64), index=True, nullable=False)
    title = Column(String(256), nullable=False)
    req_type = Column(String(32), default="FUNCTIONAL")
    priority = Column(String(32), default="MEDIUM")
    status = Column(String(32), default="DRAFT")
    acceptance_criteria_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated Requirement domain object stored as JSONB / JSON
    data = Column(JSON, nullable=False)
