"""
CodeSentinel Failures Module: Failure Database Model.

Persists Failure domain entities, correlated evidence, and grounded Root Cause Analyses in PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.types import JSON
from app.models.base import Base


class FailureModel(Base):
    """PostgreSQL relational persistence model for Failures."""
    __tablename__ = "failures"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    project_id = Column(String(36), index=True, nullable=False)
    test_execution_id = Column(String(36), index=True, nullable=True)
    test_case_id = Column(String(36), index=True, nullable=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), default="UNKNOWN", nullable=False, index=True)
    severity = Column(String(32), default="MAJOR", nullable=False, index=True)
    status = Column(String(32), default="DETECTED", nullable=False, index=True)
    occurrences_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated Failure domain object stored as JSONB / JSON
    data = Column(JSON, nullable=False)
