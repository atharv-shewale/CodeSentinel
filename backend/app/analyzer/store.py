"""
CodeSentinel Analyzer: PostgreSQL-Backed Code Analysis Store.

Persists validated CodeEntity collections into PostgreSQL per project_id.
Enables cross-process accessibility between background analyzers and API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.code_entity import CodeEntity, EntityType
from shared.schemas.common import utc_now
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.models.code_analysis import CodeAnalysisModel


class AnalysisStore:
    """
    PostgreSQL-backed store for persisting and retrieving CodeEntity collections per project.
    """

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save_entities(self, project_id: uuid.UUID | str, entities: List[CodeEntity]) -> None:
        """Persist or update CodeEntity records for a project in PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)
        now = utc_now()

        entities_payload = [e.model_dump(mode="json") for e in entities]
        total_classes = sum(1 for e in entities if e.entity_type == EntityType.CLASS)
        total_funcs = sum(1 for e in entities if e.entity_type in (EntityType.FUNCTION, EntityType.METHOD))

        async with session_maker() as session:
            try:
                stmt = select(CodeAnalysisModel).where(CodeAnalysisModel.project_id == project_id_str)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.total_entities = len(entities)
                    existing.total_classes = total_classes
                    existing.total_functions = total_funcs
                    existing.updated_at = now
                    existing.data = entities_payload
                else:
                    record = CodeAnalysisModel(
                        project_id=project_id_str,
                        total_entities=len(entities),
                        total_classes=total_classes,
                        total_functions=total_funcs,
                        created_at=now,
                        updated_at=now,
                        data=entities_payload,
                    )
                    session.add(record)

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist code analysis for project {project_id}: {e}")
                raise

    async def get_entities(self, project_id: uuid.UUID | str) -> Optional[List[CodeEntity]]:
        """Retrieve CodeEntity list for a project from PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = select(CodeAnalysisModel).where(CodeAnalysisModel.project_id == project_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record and isinstance(record.data, list):
                    return [CodeEntity.model_validate(e) for e in record.data]
                return None
            except Exception as e:
                logger.error(f"Failed to fetch code analysis for project {project_id}: {e}")
                return None

    async def delete_entities(self, project_id: uuid.UUID | str) -> bool:
        """Delete CodeEntity records for a project."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = delete(CodeAnalysisModel).where(CodeAnalysisModel.project_id == project_id_str)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete code analysis for project {project_id}: {e}")
                return False

    async def clear_all(self) -> None:
        """Clear all code analyses across database."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            try:
                stmt = delete(CodeAnalysisModel)
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to clear code analyses: {e}")

    # =========================================================================
    # Classmethod Convenience API
    # =========================================================================
    @classmethod
    async def save(cls, project_id: uuid.UUID | str, entities: List[CodeEntity]) -> None:
        await cls().save_entities(project_id, entities)

    @classmethod
    async def get(cls, project_id: uuid.UUID | str) -> Optional[List[CodeEntity]]:
        return await cls().get_entities(project_id)

    @classmethod
    async def delete(cls, project_id: uuid.UUID | str) -> bool:
        return await cls().delete_entities(project_id)

    @classmethod
    async def clear(cls) -> None:
        await cls().clear_all()
