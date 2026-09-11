"""
CodeSentinel Testing Module: TestCase Database Model.

Persists validated TestCase domain entities with strict provenance lineage in PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.types import JSON
from app.models.base import Base


class TestCaseModel(Base):
    """PostgreSQL relational persistence model for Test Cases."""
    __tablename__ = "test_cases"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    project_id = Column(String(36), index=True, nullable=False)
    name = Column(String(256), nullable=False, index=True)
    provenance = Column(String(32), nullable=False, index=True)
    test_type = Column(String(32), default="UNIT", nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    target_entity_id = Column(String(36), nullable=True, index=True)
    target_route_id = Column(String(36), nullable=True, index=True)
    requirement_id = Column(String(36), nullable=True, index=True)
    file_path = Column(String(512), nullable=False)
    execution_count = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    flakiness_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated TestCase domain object stored as JSONB / JSON
    data = Column(JSON, nullable=False)
