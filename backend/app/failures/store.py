"""
CodeSentinel Failures Module: Failure PostgreSQL Persistence Store.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.common import utc_now
from shared.schemas.failure import Failure, FailureCategory, FailureSeverity, FailureStatus
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.failures.models import FailureModel


class FailureStore:
    """PostgreSQL-backed store for persisting and querying Failure domain entities."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save(self, failure: Failure) -> Failure:
        """Persist a single Failure domain entity."""
        session_maker = self._get_sessionmaker()
        now = utc_now()
        fail_id_str = str(failure.id)
        project_id_str = str(failure.project_id)
        fail_dict = failure.model_dump(mode="json")

        async with session_maker() as session:
            try:
                stmt = select(FailureModel).where(FailureModel.id == fail_id_str)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.title = failure.title
                    existing.category = failure.category.value
                    existing.severity = failure.severity.value
                    existing.status = failure.status.value
                    existing.occurrences_count = failure.occurrences_count
                    existing.updated_at = now
                    existing.data = fail_dict
                else:
                    record = FailureModel(
                        id=fail_id_str,
                        project_id=project_id_str,
                        test_execution_id=str(failure.test_execution_id) if failure.test_execution_id else None,
                        test_case_id=str(failure.test_case_id) if failure.test_case_id else None,
                        title=failure.title,
                        category=failure.category.value,
                        severity=failure.severity.value,
                        status=failure.status.value,
                        occurrences_count=failure.occurrences_count,
                        created_at=failure.created_at or now,
                        updated_at=now,
                        data=fail_dict,
                    )
                    session.add(record)

                await session.commit()
                return failure
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist failure {failure.id}: {e}")
                raise

    async def get(self, failure_id: uuid.UUID | str) -> Optional[Failure]:
        """Fetch a single Failure by UUID."""
        session_maker = self._get_sessionmaker()
        fail_id_str = str(failure_id)

        async with session_maker() as session:
            try:
                stmt = select(FailureModel).where(FailureModel.id == fail_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if record and record.data:
                    return Failure.model_validate(record.data)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch failure {failure_id}: {e}")
                return None

    async def list(
        self,
        project_id: Optional[uuid.UUID | str] = None,
        category: Optional[FailureCategory | str] = None,
        severity: Optional[FailureSeverity | str] = None,
        status: Optional[FailureStatus | str] = None,
    ) -> List[Failure]:
        """Query failures filtered by project, category, severity, or status."""
        session_maker = self._get_sessionmaker()

        async with session_maker() as session:
            try:
                stmt = select(FailureModel)
                if project_id:
                    stmt = stmt.where(FailureModel.project_id == str(project_id))
                if category:
                    cat_val = category.value if isinstance(category, FailureCategory) else str(category)
                    stmt = stmt.where(FailureModel.category == cat_val)
                if severity:
                    sev_val = severity.value if isinstance(severity, FailureSeverity) else str(severity)
                    stmt = stmt.where(FailureModel.severity == sev_val)
                if status:
                    stat_val = status.value if isinstance(status, FailureStatus) else str(status)
                    stmt = stmt.where(FailureModel.status == stat_val)

                stmt = stmt.order_by(FailureModel.created_at.desc())
                result = await session.execute(stmt)
                records = result.scalars().all()
                return [Failure.model_validate(r.data) for r in records if r.data]
            except Exception as e:
                logger.error(f"Failed to query failures: {e}")
                return []

    async def delete(self, failure_id: uuid.UUID | str) -> bool:
        """Delete a single Failure by UUID."""
        session_maker = self._get_sessionmaker()
        fail_id_str = str(failure_id)

        async with session_maker() as session:
            try:
                stmt = delete(FailureModel).where(FailureModel.id == fail_id_str)
                res = await session.execute(stmt)
                await session.commit()
                return res.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete failure {failure_id}: {e}")
                return False
