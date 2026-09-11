"""
CodeSentinel Core: PostgreSQL-Backed Project Store.

Replaces process-local in-memory registries with relational PostgreSQL persistence.
Ensures projects written by background workers are immediately visible across web processes.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.project import Project
from app.core.database import get_sessionmaker, init_db
from app.core.logging import logger
from app.models.project import ProjectModel


class ProjectStore:
    """
    PostgreSQL-backed store for persisting and retrieving Project domain entities.

    Can be instantiated with a custom session_factory for cross-process isolation testing,
    or used via classmethods against the default database connection pool.
    """

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save_project(self, project: Project) -> Project:
        """Persist or update a Project in PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project.id)
        project_dict = project.model_dump(mode="json")

        async with session_maker() as session:
            try:
                stmt = select(ProjectModel).where(ProjectModel.id == project_id_str)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.name = project.name[:128]
                    existing.repository_url = str(project.repository_url)
                    existing.default_branch = project.default_branch
                    existing.provider = project.provider.value if hasattr(project.provider, "value") else str(project.provider)
                    existing.status = project.status.value if hasattr(project.status, "value") else str(project.status)
                    existing.updated_at = project.updated_at
                    existing.total_files = str(project.total_files)
                    existing.total_lines_of_code = str(project.total_lines_of_code)
                    existing.data = project_dict
                else:
                    new_record = ProjectModel(
                        id=project_id_str,
                        name=project.name[:128],
                        repository_url=str(project.repository_url),
                        default_branch=project.default_branch,
                        provider=project.provider.value if hasattr(project.provider, "value") else str(project.provider),
                        status=project.status.value if hasattr(project.status, "value") else str(project.status),
                        created_at=project.created_at,
                        updated_at=project.updated_at,
                        total_files=str(project.total_files),
                        total_lines_of_code=str(project.total_lines_of_code),
                        data=project_dict,
                    )
                    session.add(new_record)

                await session.commit()
                return project
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist project {project.id} in database: {e}")
                raise

    async def get_project(self, project_id: uuid.UUID | str) -> Optional[Project]:
        """Fetch a Project by UUID from PostgreSQL."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        async with session_maker() as session:
            try:
                stmt = select(ProjectModel).where(ProjectModel.id == project_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record and record.data:
                    return Project.model_validate(record.data)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch project {project_id} from database: {e}")
                return None

    async def list_all_projects(self) -> List[Project]:
        """List all projects stored in PostgreSQL."""
        session_maker = self._get_sessionmaker()

        async with session_maker() as session:
            try:
                stmt = select(ProjectModel).order_by(ProjectModel.created_at.desc())
                result = await session.execute(stmt)
                records = result.scalars().all()
                return [Project.model_validate(r.data) for r in records if r.data]
            except Exception as e:
                logger.error(f"Failed to list projects from database: {e}")
                return []

    async def delete_project(self, project_id: uuid.UUID | str) -> bool:
        """Delete a Project by UUID from PostgreSQL and remove its disk workspace."""
        session_maker = self._get_sessionmaker()
        project_id_str = str(project_id)

        # Remove disk directory if exists
        try:
            existing = await self.get_project(project_id)
            if existing and existing.metadata and existing.metadata.get("root_dir"):
                root_dir = existing.metadata["root_dir"]
                if os.path.exists(root_dir):
                    shutil.rmtree(root_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Error cleaning up disk workspace for project {project_id}: {e}")

        async with session_maker() as session:
            try:
                stmt = delete(ProjectModel).where(ProjectModel.id == project_id_str)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete project {project_id} from database: {e}")
                return False

    async def clear_all(self) -> None:
        """Remove all projects (used for test setup/teardown)."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            try:
                stmt = delete(ProjectModel)
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to clear projects from database: {e}")

    # =========================================================================
    # Classmethod Convenience API (Default Connection)
    # =========================================================================
    @classmethod
    async def save(cls, project: Project) -> Project:
        return await cls().save_project(project)

    @classmethod
    async def get(cls, project_id: uuid.UUID | str) -> Optional[Project]:
        return await cls().get_project(project_id)

    @classmethod
    async def list_all(cls) -> List[Project]:
        return await cls().list_all_projects()

    @classmethod
    async def delete(cls, project_id: uuid.UUID | str) -> bool:
        return await cls().delete_project(project_id)

    @classmethod
    async def clear(cls) -> None:
        await cls().clear_all()
