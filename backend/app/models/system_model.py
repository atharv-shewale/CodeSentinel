"""
CodeSentinel Models: Software System Model Database Model.

Persists the assembled project-wide Software System Model in PostgreSQL ready for Module 3 (Neo4j).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String
from sqlalchemy.types import JSON
from .base import Base


class SystemModelRecord(Base):
    """PostgreSQL relational persistence model for the complete Software System Model."""
    __tablename__ = "software_system_models"

    project_id = Column(String(36), primary_key=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Full structured Software System Model graph
    data = Column(JSON, nullable=False)
