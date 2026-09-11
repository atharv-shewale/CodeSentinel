"""
CodeSentinel Requirements: PostgreSQL-Backed Requirement Store.

Persists validated Requirement domain entities into PostgreSQL per project_id.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.common import utc_now
from shared.schemas.requirement import Requirement
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.models.requirement import RequirementModel


class RequirementStore:
    """PostgreSQL-backed repository for Project Requirements."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save_requirements(self, project_id: uuid.UUID | str, requirements: List[Requirement]) -> None:
        """Persist or update Requirement records in PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)
        now = utc_now()

        async with session_maker() as session:
            try:
                for req in requirements:
                    req_id_str = str(req.id)
                    req_dict = req.model_dump(mode="json")

                    stmt = select(RequirementModel).where(RequirementModel.id == req_id_str)
                    res = await session.execute(stmt)
                    existing = res.scalar_one_or_none()

                    if existing:
                        existing.identifier = req.identifier
                        existing.title = req.title
                        existing.req_type = req.req_type.value if hasattr(req.req_type, "value") else str(req.req_type)
                        existing.priority = req.priority.value if hasattr(req.priority, "value") else str(req.priority)
                        existing.status = req.status.value if hasattr(req.status, "value") else str(req.status)
                        existing.acceptance_criteria_count = len(req.acceptance_criteria)
                        existing.updated_at = now
                        existing.data = req_dict
                    else:
                        record = RequirementModel(
                            id=req_id_str,
                            project_id=project_id_str,
                            identifier=req.identifier,
                            title=req.title,
                            req_type=req.req_type.value if hasattr(req.req_type, "value") else str(req.req_type),
                            priority=req.priority.value if hasattr(req.priority, "value") else str(req.priority),
                            status=req.status.value if hasattr(req.status, "value") else str(req.status),
                            acceptance_criteria_count=len(req.acceptance_criteria),
                            created_at=req.created_at or now,
                            updated_at=now,
                            data=req_dict,
                        )
                        session.add(record)

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist requirements for project {project_id}: {e}")
                raise

    async def get_requirements(self, project_id: uuid.UUID | str) -> List[Requirement]:
        """Fetch all requirements for a project from PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = select(RequirementModel).where(RequirementModel.project_id == project_id_str).order_by(RequirementModel.identifier)
                result = await session.execute(stmt)
                records = result.scalars().all()
                return [Requirement.model_validate(r.data) for r in records if r.data]
            except Exception as e:
                logger.error(f"Failed to fetch requirements for project {project_id}: {e}")
                return []

    async def delete_requirements(self, project_id: uuid.UUID | str) -> bool:
        """Delete all requirements for a project."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = delete(RequirementModel).where(RequirementModel.project_id == project_id_str)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete requirements for project {project_id}: {e}")
                return False

    async def clear_all(self) -> None:
        """Clear all requirements across database."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            try:
                stmt = delete(RequirementModel)
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to clear requirements: {e}")

    # =========================================================================
    # Classmethod Convenience API
    # =========================================================================
    @classmethod
    async def save(cls, project_id: uuid.UUID | str, requirements: List[Requirement]) -> None:
        await cls().save_requirements(project_id, requirements)

    @classmethod
    async def get(cls, project_id: uuid.UUID | str) -> List[Requirement]:
        return await cls().get_requirements(project_id)

    @classmethod
    async def delete(cls, project_id: uuid.UUID | str) -> bool:
        return await cls().delete_requirements(project_id)

    @classmethod
    async def clear(cls) -> None:
        await cls().clear_all()
