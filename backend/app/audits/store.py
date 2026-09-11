"""
CodeSentinel Audits Module: AuditFinding PostgreSQL Persistence Store.
"""

from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from shared.schemas.audit import AuditCategory, AuditFinding, AuditSeverity, AuditStatus
from shared.schemas.common import utc_now
from app.audits.models import AuditFindingModel
from app.core.database import get_sessionmaker
from app.core.logging import logger


class AuditFindingStore:
    """PostgreSQL-backed store for persisting and querying frozen AuditFinding domain entities."""

    def __init__(self, session_factory: Optional[async_sessionmaker[AsyncSession]] = None):
        self._session_factory = session_factory

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is not None:
            return self._session_factory
        return get_sessionmaker()

    async def save(self, finding: AuditFinding) -> AuditFinding:
        """Persist a single AuditFinding domain entity."""
        saved = await self.save_many([finding])
        return saved[0]

    async def save_many(self, findings: List[AuditFinding]) -> List[AuditFinding]:
        """Persist multiple AuditFinding domain entities in a single transaction."""
        if not findings:
            return []

        session_maker = self._get_sessionmaker()
        now = utc_now()

        async with session_maker() as session:
            try:
                for f in findings:
                    f_id_str = str(f.id)
                    project_id_str = str(f.project_id)
                    f_dict = f.model_dump(mode="json")

                    stmt = select(AuditFindingModel).where(AuditFindingModel.id == f_id_str)
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()

                    if existing:
                        existing.rule_id = f.rule_id
                        existing.title = f.title
                        existing.category = f.category.value
                        existing.severity = f.severity.value
                        existing.status = f.status.value
                        existing.standard = f.standard.value if f.standard else None
                        existing.cvss_score = f.cvss_score
                        existing.file_path = f.location.file_path
                        existing.target_entity_id = str(f.target_entity_id) if f.target_entity_id else None
                        existing.updated_at = now
                        existing.data = f_dict
                    else:
                        new_model = AuditFindingModel(
                            id=f_id_str,
                            project_id=project_id_str,
                            rule_id=f.rule_id,
                            title=f.title,
                            category=f.category.value,
                            severity=f.severity.value,
                            status=f.status.value,
                            standard=f.standard.value if f.standard else None,
                            cvss_score=f.cvss_score,
                            file_path=f.location.file_path,
                            target_entity_id=str(f.target_entity_id) if f.target_entity_id else None,
                            created_at=f.created_at or now,
                            updated_at=f.updated_at or now,
                            data=f_dict,
                        )
                        session.add(new_model)

                await session.commit()
                return findings
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to persist audit findings: {e}")
                raise

    async def get_by_id(self, finding_id: uuid.UUID) -> Optional[AuditFinding]:
        """Fetch an AuditFinding by UUID."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            stmt = select(AuditFindingModel).where(AuditFindingModel.id == str(finding_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            return AuditFinding.model_validate(model.data)

    async def list_for_project(
        self,
        project_id: uuid.UUID,
        severity: Optional[AuditSeverity] = None,
        category: Optional[AuditCategory] = None,
        status: Optional[AuditStatus] = None,
    ) -> List[AuditFinding]:
        """List audit findings for a project with optional filters."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            query = select(AuditFindingModel).where(AuditFindingModel.project_id == str(project_id))
            if severity:
                s_val = severity.value if hasattr(severity, "value") else str(severity)
                query = query.where(AuditFindingModel.severity == s_val)
            if category:
                c_val = category.value if hasattr(category, "value") else str(category)
                query = query.where(AuditFindingModel.category == c_val)
            if status:
                st_val = status.value if hasattr(status, "value") else str(status)
                query = query.where(AuditFindingModel.status == st_val)

            result = await session.execute(query)
            models = result.scalars().all()
            return [AuditFinding.model_validate(m.data) for m in models]

    async def delete_for_project(self, project_id: uuid.UUID) -> int:
        """Delete all audit findings for a project."""
        session_maker = self._get_sessionmaker()
        async with session_maker() as session:
            stmt = delete(AuditFindingModel).where(AuditFindingModel.project_id == str(project_id))
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount or 0
