"""
CodeSentinel Sandbox Module: TestExecution Database Model.

Persists TestExecution domain entities and container execution telemetry in PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.types import JSON
from app.models.base import Base


class TestExecutionModel(Base):
    """PostgreSQL relational persistence model for Test Executions."""
    __tablename__ = "test_executions"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    project_id = Column(String(36), index=True, nullable=False)
    status = Column(String(32), default="QUEUED", nullable=False, index=True)
    triggered_by = Column(String(128), default="SYSTEM", nullable=False)
    environment = Column(String(64), default="DOCKER_SANDBOX", nullable=False)
    commit_sha = Column(String(64), nullable=True)
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    errored_tests = Column(Integer, default=0)
    total_duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated TestExecution domain object stored as JSONB / JSON
    data = Column(JSON, nullable=False)
