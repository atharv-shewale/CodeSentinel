"""
CodeSentinel Analyzer: Software System Model Schema & Builder.

Assembles the unified, multi-dimensional system graph (files -> classes -> functions
-> APIs -> dependencies -> requirements -> code-requirement links) for Module 3 (Neo4j).
Persists assembled models in PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.code_entity import CodeEntity, EntityType
from shared.schemas.common import utc_now
from shared.schemas.project import Project
from shared.schemas.requirement import Requirement
from app.analyzer.mapper import CodeRequirementLink
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.models.system_model import SystemModelRecord


class FileNode(BaseModel):
    """File structural node in the system model."""
    file_path: str
    language: str
    total_lines: int
    classes: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    imports: List[str] = Field(default_factory=list)


class SoftwareSystemModel(BaseModel):
    """
    Unified Software System Model representing the analyzed codebase.
    Primary contract deliverable from Module 2 to Module 3 (Knowledge Graph / Neo4j).
    """
    project_id: uuid.UUID = Field(..., description="Project UUID identifier.")
    project_name: str = Field(..., description="Project display name.")
    generated_at: str = Field(..., description="ISO 8601 generation timestamp.")
    total_files: int = Field(0)
    total_classes: int = Field(0)
    total_functions: int = Field(0)
    total_requirements: int = Field(0)
    total_links: int = Field(0)
    files: List[FileNode] = Field(default_factory=list)
    classes: List[CodeEntity] = Field(default_factory=list)
    functions: List[CodeEntity] = Field(default_factory=list)
    entities: List[CodeEntity] = Field(default_factory=list, description="All parsed structural code entities.")
    apis: List[Dict[str, Any]] = Field(default_factory=list, description="Cross-referenced API routes from Module 1.")
    routes: List[Dict[str, Any]] = Field(default_factory=list, description="All detected route endpoints.")
    dependencies: Dict[str, Any] = Field(default_factory=dict, description="Extracted package dependencies.")
    requirements: List[Requirement] = Field(default_factory=list)
    mappings: List[CodeRequirementLink] = Field(default_factory=list)
    unmapped_requirements: List[Requirement] = Field(default_factory=list)
    unmapped_entities_count: int = Field(0)


class SystemModelStore:
    """PostgreSQL-backed store for persisting and retrieving Software System Models."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save_system_model(self, model: SoftwareSystemModel) -> None:
        """Persist or update a SoftwareSystemModel in PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(model.project_id)
        now = utc_now()
        model_dict = model.model_dump(mode="json")

        async with session_maker() as session:
            try:
                stmt = select(SystemModelRecord).where(SystemModelRecord.project_id == project_id_str)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.updated_at = now
                    existing.data = model_dict
                else:
                    record = SystemModelRecord(
                        project_id=project_id_str,
                        created_at=now,
                        updated_at=now,
                        data=model_dict,
                    )
                    session.add(record)

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist SoftwareSystemModel for project {model.project_id}: {e}")
                raise

    async def get_system_model(self, project_id: uuid.UUID | str) -> Optional[SoftwareSystemModel]:
        """Fetch SoftwareSystemModel from PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = select(SystemModelRecord).where(SystemModelRecord.project_id == project_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record and record.data:
                    return SoftwareSystemModel.model_validate(record.data)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch SoftwareSystemModel for project {project_id}: {e}")
                return None

    # =========================================================================
    # Classmethod Convenience API
    # =========================================================================
    @classmethod
    async def save(cls, model: SoftwareSystemModel) -> None:
        await cls().save_system_model(model)

    @classmethod
    async def get(cls, project_id: uuid.UUID | str) -> Optional[SoftwareSystemModel]:
        return await cls().get_system_model(project_id)


class SystemModelBuilder:
    """Constructs the SoftwareSystemModel by joining code analysis, profiler, and requirements."""

    @classmethod
    def assemble_system_model(
        cls,
        project_id: uuid.UUID,
        project_name: str,
        code_entities: List[CodeEntity],
        requirements: List[Requirement],
        links: List[CodeRequirementLink],
        unmapped_requirements: List[Requirement],
        unmapped_entities: List[CodeEntity],
        profile_apis: Optional[List[Dict[str, Any]]] = None,
        profile_dependencies: Optional[Dict[str, Any]] = None,
    ) -> SoftwareSystemModel:
        """Join all multi-dimensional intelligence into a unified SoftwareSystemModel."""
        # Categorize Code Entities
        file_entities = [e for e in code_entities if e.entity_type == EntityType.FILE]
        class_entities = [e for e in code_entities if e.entity_type == EntityType.CLASS]
        func_entities = [e for e in code_entities if e.entity_type in (EntityType.FUNCTION, EntityType.METHOD)]

        # Build FileNodes
        file_nodes: List[FileNode] = []
        for fe in file_entities:
            f_path = fe.location.file_path
            f_classes = [c.name for c in class_entities if c.location.file_path == f_path]
            f_funcs = [f.name for f in func_entities if f.location.file_path == f_path]
            f_imports = fe.dependencies or []

            file_nodes.append(
                FileNode(
                    file_path=f_path,
                    language=fe.language,
                    total_lines=fe.metadata.get("total_lines", fe.location.end_line),
                    classes=f_classes,
                    functions=f_funcs,
                    imports=f_imports,
                )
            )

        return SoftwareSystemModel(
            project_id=project_id,
            project_name=project_name,
            generated_at=utc_now().isoformat(),
            total_files=len(file_entities),
            total_classes=len(class_entities),
            total_functions=len(func_entities),
            total_requirements=len(requirements),
            total_links=len(links),
            files=file_nodes,
            classes=class_entities,
            functions=func_entities,
            entities=code_entities,
            apis=profile_apis or [],
            routes=profile_apis or [],
            dependencies=profile_dependencies or {},
            requirements=requirements,
            mappings=links,
            unmapped_requirements=unmapped_requirements,
            unmapped_entities_count=len(unmapped_entities),
        )
