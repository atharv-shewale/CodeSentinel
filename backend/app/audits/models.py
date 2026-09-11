"""
CodeSentinel Audits Module: AuditFinding Database Model.

Persists frozen AuditFinding domain entities in PostgreSQL.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy.types import JSON
from app.models.base import Base


class AuditFindingModel(Base):
    """PostgreSQL relational persistence model for Audit Findings."""
    __tablename__ = "audit_findings"

    id = Column(String(36), primary_key=True, index=True, nullable=False)
    project_id = Column(String(36), index=True, nullable=False)
    rule_id = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    status = Column(String(32), default="OPEN", nullable=False, index=True)
    standard = Column(String(64), nullable=True)
    cvss_score = Column(Float, nullable=True)
    file_path = Column(String(512), nullable=False)
    target_entity_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated AuditFinding domain object stored as JSON
    data = Column(JSON, nullable=False)
