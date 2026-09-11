"""
CodeSentinel Sandbox Module: TestExecution PostgreSQL Persistence Store.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.common import utc_now
from shared.schemas.test_execution import ExecutionStatus, TestExecution
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.sandbox.models import TestExecutionModel


class TestExecutionStore:
    """PostgreSQL-backed store for persisting and querying TestExecution domain entities."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save(self, execution: TestExecution) -> TestExecution:
        """Persist a single TestExecution domain entity."""
        session_maker = self._get_sessionmaker()
        now = utc_now()
        exec_id_str = str(execution.id)
        project_id_str = str(execution.project_id)
        exec_dict = execution.model_dump(mode="json")

        async with session_maker() as session:
            try:
                stmt = select(TestExecutionModel).where(TestExecutionModel.id == exec_id_str)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.status = execution.status.value
                    existing.total_tests = execution.total_tests
                    existing.passed_tests = execution.passed_tests
                    existing.failed_tests = execution.failed_tests
                    existing.errored_tests = execution.errored_tests
                    existing.total_duration_ms = execution.total_duration_ms
                    existing.updated_at = now
                    existing.data = exec_dict
                else:
                    record = TestExecutionModel(
                        id=exec_id_str,
                        project_id=project_id_str,
                        status=execution.status.value,
                        triggered_by=execution.triggered_by,
                        environment=execution.environment.value,
                        commit_sha=execution.commit_sha,
                        total_tests=execution.total_tests,
                        passed_tests=execution.passed_tests,
                        failed_tests=execution.failed_tests,
                        errored_tests=execution.errored_tests,
                        total_duration_ms=execution.total_duration_ms,
                        created_at=execution.created_at or now,
                        updated_at=now,
                        data=exec_dict,
                    )
                    session.add(record)

                await session.commit()
                return execution
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist test execution {execution.id}: {e}")
                raise

    async def get(self, execution_id: uuid.UUID | str) -> Optional[TestExecution]:
        """Fetch a single TestExecution by UUID."""
        session_maker = self._get_sessionmaker()
        exec_id_str = str(execution_id)

        async with session_maker() as session:
            try:
                stmt = select(TestExecutionModel).where(TestExecutionModel.id == exec_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if record and record.data:
                    return TestExecution.model_validate(record.data)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch test execution {execution_id}: {e}")
                return None

    async def list(
        self,
        project_id: Optional[uuid.UUID | str] = None,
        status: Optional[ExecutionStatus | str] = None,
    ) -> List[TestExecution]:
        """Query test executions by project or status."""
        session_maker = self._get_sessionmaker()

        async with session_maker() as session:
            try:
                stmt = select(TestExecutionModel)
                if project_id:
                    stmt = stmt.where(TestExecutionModel.project_id == str(project_id))
                if status:
                    stat_val = status.value if isinstance(status, ExecutionStatus) else str(status)
                    stmt = stmt.where(TestExecutionModel.status == stat_val)

                stmt = stmt.order_by(TestExecutionModel.created_at.desc())
                result = await session.execute(stmt)
                records = result.scalars().all()
                return [TestExecution.model_validate(r.data) for r in records if r.data]
            except Exception as e:
                logger.error(f"Failed to query test executions: {e}")
                return []

    async def delete(self, execution_id: uuid.UUID | str) -> bool:
        """Delete a single TestExecution by UUID."""
        session_maker = self._get_sessionmaker()
        exec_id_str = str(execution_id)

        async with session_maker() as session:
            try:
                stmt = delete(TestExecutionModel).where(TestExecutionModel.id == exec_id_str)
                res = await session.execute(stmt)
                await session.commit()
                return res.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete test execution {execution_id}: {e}")
                return False
