"""
CodeSentinel Requirements: Service Orchestrator.

Manages requirement document uploads, format-aware extraction, strict criteria validation,
and PostgreSQL persistence.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional
import uuid
from shared.schemas.jobs import JobStatus, JobType
from shared.schemas.requirement import Requirement
from app.core.logging import logger
from app.requirements.extractor import (
    DocumentParsingError,
    DocumentReader,
    RequirementExtractor,
)
from app.requirements.store import RequirementStore
from app.workers.job_manager import JobManager


class RequirementService:
    """Orchestrates document ingestion and requirement entity extraction."""

    @classmethod
    async def process_document(
        cls,
        project_id: uuid.UUID,
        file_content: bytes,
        filename: str,
    ) -> List[Requirement]:
        """
        Parse uploaded specification document, extract requirements, and persist in PostgreSQL.
        """
        # 1. Read document text
        text = DocumentReader.read_document_text(file_content, filename)

        # 2. Extract strictly-validated Requirement domain entities
        requirements = RequirementExtractor.extract_from_text(
            text=text,
            project_id=project_id,
            source_name=filename,
        )

        # 3. Persist in PostgreSQL
        if requirements:
            await RequirementStore.save(project_id, requirements)

        return requirements

    @classmethod
    async def process_raw_text(
        cls,
        project_id: uuid.UUID,
        text: str,
        source_name: str = "text_input",
    ) -> List[Requirement]:
        """Parse raw requirement text and persist in PostgreSQL."""
        requirements = RequirementExtractor.extract_from_text(
            text=text,
            project_id=project_id,
            source_name=source_name,
        )

        if requirements:
            await RequirementStore.save(project_id, requirements)

        return requirements

    @classmethod
    async def start_extraction_job(
        cls,
        project_id: uuid.UUID,
        file_content: bytes,
        filename: str,
    ) -> JobStatus:
        """Enqueue asynchronous requirement extraction background job."""
        job = await JobManager.create_job(
            job_type=JobType.REQUIREMENTS_PARSING,
            total_steps=100,
            initial_message=f"Queued requirement document parsing for '{filename}'...",
        )

        async def _pipeline():
            try:
                await JobManager.update_progress(job.job_id, 30, f"Reading and decoding document '{filename}'...")
                reqs = await cls.process_document(project_id=project_id, file_content=file_content, filename=filename)
                await JobManager.update_progress(job.job_id, 90, f"Extracted {len(reqs)} requirements with strict acceptance criteria...")
                await JobManager.complete_job(
                    job.job_id,
                    result=[r.model_dump(mode="json") for r in reqs],
                    message=f"Extracted {len(reqs)} requirement entities from '{filename}'.",
                )
            except DocumentParsingError as e:
                logger.error(f"Requirement extraction job {job.job_id} failed: {e}")
                await JobManager.fail_job(job.job_id, f"{e.code}: {e.message}")
            except Exception as e:
                logger.exception(f"Requirement extraction job {job.job_id} failed unexpectedly: {e}")
                await JobManager.fail_job(job.job_id, f"EXTRACTION_FAILED: {str(e)}")

        asyncio.create_task(_pipeline())
        return job
