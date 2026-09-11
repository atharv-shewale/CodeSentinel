"""
CodeSentinel Testing Module: TestCase PostgreSQL Persistence Store.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.common import utc_now
from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from app.core.database import get_sessionmaker
from app.core.logging import logger
from app.testing.models import TestCaseModel


class TestCaseStore:
    """PostgreSQL-backed store for persisting and querying TestCase domain entities."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save(self, test_case: TestCase) -> TestCase:
        """Persist a single TestCase domain entity."""
        saved = await self.save_many([test_case])
        return saved[0]

    async def save_many(self, test_cases: List[TestCase]) -> List[TestCase]:
        """Persist multiple TestCase domain entities in a single transaction."""
        if not test_cases:
            return []

        session_maker = self._get_sessionmaker()
        now = utc_now()

        async with session_maker() as session:
            try:
                for tc in test_cases:
                    tc_id_str = str(tc.id)
                    project_id_str = str(tc.project_id)
                    tc_dict = tc.model_dump(mode="json")

                    stmt = select(TestCaseModel).where(TestCaseModel.id == tc_id_str)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        existing.name = tc.name
                        existing.provenance = tc.provenance.value
                        existing.test_type = tc.test_type.value
                        existing.status = tc.status.value
                        existing.target_entity_id = str(tc.target_entity_id) if tc.target_entity_id else None
                        existing.target_route_id = str(tc.target_route_id) if tc.target_route_id else None
                        existing.requirement_id = str(tc.requirement_id) if tc.requirement_id else None
                        existing.file_path = tc.file_path
                        existing.execution_count = tc.execution_count
                        existing.pass_count = tc.pass_count
                        existing.fail_count = tc.fail_count
                        existing.flakiness_score = tc.flakiness_score
                        existing.updated_at = now
                        existing.data = tc_dict
                    else:
                        record = TestCaseModel(
                            id=tc_id_str,
                            project_id=project_id_str,
                            name=tc.name,
                            provenance=tc.provenance.value,
                            test_type=tc.test_type.value,
                            status=tc.status.value,
                            target_entity_id=str(tc.target_entity_id) if tc.target_entity_id else None,
                            target_route_id=str(tc.target_route_id) if tc.target_route_id else None,
                            requirement_id=str(tc.requirement_id) if tc.requirement_id else None,
                            file_path=tc.file_path,
                            execution_count=tc.execution_count,
                            pass_count=tc.pass_count,
                            fail_count=tc.fail_count,
                            flakiness_score=tc.flakiness_score,
                            created_at=tc.created_at or now,
                            updated_at=now,
                            data=tc_dict,
                        )
                        session.add(record)

                await session.commit()
                return test_cases
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist {len(test_cases)} test cases: {e}")
                raise

    async def get(self, test_id: uuid.UUID | str) -> Optional[TestCase]:
        """Fetch a single TestCase by UUID."""
        session_maker = self._get_sessionmaker()
        test_id_str = str(test_id)

        async with session_maker() as session:
            try:
                stmt = select(TestCaseModel).where(TestCaseModel.id == test_id_str)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                if record and record.data:
                    return TestCase.model_validate(record.data)
                return None
            except Exception as e:
                logger.error(f"Failed to fetch test case {test_id}: {e}")
                return None

    async def list(
        self,
        project_id: Optional[uuid.UUID | str] = None,
        provenance: Optional[TestProvenance | str] = None,
        test_type: Optional[TestType | str] = None,
        status: Optional[TestStatus | str] = None,
    ) -> List[TestCase]:
        """Query test cases by project, provenance, test_type, or status."""
        session_maker = self._get_sessionmaker()

        async with session_maker() as session:
            try:
                stmt = select(TestCaseModel)
                if project_id:
                    stmt = stmt.where(TestCaseModel.project_id == str(project_id))
                if provenance:
                    prov_val = provenance.value if isinstance(provenance, TestProvenance) else str(provenance)
                    stmt = stmt.where(TestCaseModel.provenance == prov_val)
                if test_type:
                    type_val = test_type.value if isinstance(test_type, TestType) else str(test_type)
                    stmt = stmt.where(TestCaseModel.test_type == type_val)
                if status:
                    stat_val = status.value if isinstance(status, TestStatus) else str(status)
                    stmt = stmt.where(TestCaseModel.status == stat_val)

                stmt = stmt.order_by(TestCaseModel.created_at.desc())
                result = await session.execute(stmt)
                records = result.scalars().all()
                return [TestCase.model_validate(r.data) for r in records if r.data]
            except Exception as e:
                logger.error(f"Failed to query test cases: {e}")
                return []

    async def delete(self, test_id: uuid.UUID | str) -> bool:
        """Delete a single TestCase by UUID."""
        session_maker = self._get_sessionmaker()
        test_id_str = str(test_id)

        async with session_maker() as session:
            try:
                stmt = delete(TestCaseModel).where(TestCaseModel.id == test_id_str)
                res = await session.execute(stmt)
                await session.commit()
                return res.rowcount > 0
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete test case {test_id}: {e}")
                return False

    @classmethod
    async def save_test(cls, test_case: TestCase) -> TestCase:
        return await cls().save(test_case)

    @classmethod
    async def save_tests(cls, test_cases: List[TestCase]) -> List[TestCase]:
        return await cls().save_many(test_cases)

    @classmethod
    async def get_test(cls, test_id: uuid.UUID | str) -> Optional[TestCase]:
        return await cls().get(test_id)

    @classmethod
    async def list_tests(
        cls,
        project_id: Optional[uuid.UUID | str] = None,
        provenance: Optional[TestProvenance | str] = None,
        test_type: Optional[TestType | str] = None,
        status: Optional[TestStatus | str] = None,
    ) -> List[TestCase]:
        return await cls().list(project_id=project_id, provenance=provenance, test_type=test_type, status=status)
