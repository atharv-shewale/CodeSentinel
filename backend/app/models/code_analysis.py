"""
CodeSentinel Models: Code Analysis Database Model.

Persists validated CodeEntity collections and AST extraction results per project in PostgreSQL.
"""

from __future__ import annotations

import uuid
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.types import JSON
from .base import Base


class CodeAnalysisModel(Base):
    """PostgreSQL relational persistence model for CodeEntity analysis results."""
    __tablename__ = "code_analyses"

    project_id = Column(String(36), primary_key=True, index=True, nullable=False)
    total_entities = Column(Integer, nullable=False, default=0)
    total_classes = Column(Integer, nullable=False, default=0)
    total_functions = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Complete validated CodeEntity list and AST graph stored as JSONB / JSON
    data = Column(JSON, nullable=False)
