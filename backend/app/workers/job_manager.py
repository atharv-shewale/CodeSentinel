"""
CodeSentinel Backend: Redis Job Manager.

Provides job dispatching, real-time progress updates, and status queries
for background tasks across all modules. Includes in-memory fallback for
offline testing.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
import uuid
import redis.asyncio as aioredis
from shared.schemas.common import utc_now
from shared.schemas.jobs import JobProgress, JobState, JobStatus, JobType
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import get_redis

# In-memory fallback dictionary for testing or when Redis is offline
_in_memory_job_store: Dict[str, JobStatus] = {}


class JobManager:
    """Orchestrates job state persistence, queue push, and status retrieval."""

    @staticmethod
    async def create_job(
        job_type: JobType,
        job_id: Optional[str] = None,
        total_steps: int = 100,
        initial_message: str = "Job queued...",
    ) -> JobStatus:
        """
        Register a new background job with PENDING state and push to the queue.
        """
        if not job_id:
            job_id = str(uuid.uuid4())

        now = utc_now()
        job = JobStatus(
            job_id=job_id,
            job_type=job_type,
            status=JobState.PENDING,
            progress=JobProgress(
                current_step=0,
                total_steps=total_steps,
                percentage=0.0,
                status_message=initial_message,
            ),
            result=None,
            error=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )

        # Store in memory
        _in_memory_job_store[job_id] = job

        try:
            r = await get_redis()
            payload = job.model_dump_json()
            key = f"{settings.REDIS_JOB_PREFIX}{job_id}"
            await r.set(key, payload)
            await r.rpush(settings.REDIS_JOB_QUEUE, job_id)
            logger.info(f"Enqueued job {job_id} of type {job_type} to Redis.")
        except Exception as e:
            logger.warning(f"Redis unavailable, saved job {job_id} to in-memory store: {e}")

        return job

    @staticmethod
    async def update_progress(
        job_id: str,
        current_step: int,
        status_message: str,
        total_steps: Optional[int] = None,
    ) -> Optional[JobStatus]:
        """Update the progress of a running job."""
        job = await JobManager.get_job(job_id)
        if not job:
            return None

        total = total_steps if total_steps is not None else job.progress.total_steps
        percentage = min(100.0, max(0.0, (current_step / total) * 100.0)) if total > 0 else 0.0

        job.status = JobState.RUNNING
        job.progress.current_step = current_step
        job.progress.total_steps = total
        job.progress.percentage = round(percentage, 2)
        job.progress.status_message = status_message
        job.updated_at = utc_now()

        _in_memory_job_store[job_id] = job

        try:
            r = await get_redis()
            key = f"{settings.REDIS_JOB_PREFIX}{job_id}"
            await r.set(key, job.model_dump_json())
        except Exception as e:
            logger.debug(f"Redis update failed, updated in-memory store for {job_id}: {e}")

        return job

    @staticmethod
    async def complete_job(
        job_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Job completed successfully.",
    ) -> Optional[JobStatus]:
        """Mark a job as COMPLETED with output payload."""
        job = await JobManager.get_job(job_id)
        if not job:
            return None

        now = utc_now()
        job.status = JobState.COMPLETED
        job.progress.current_step = job.progress.total_steps
        job.progress.percentage = 100.0
        job.progress.status_message = message
        job.result = result or {}
        job.updated_at = now
        job.completed_at = now

        _in_memory_job_store[job_id] = job

        try:
            r = await get_redis()
            key = f"{settings.REDIS_JOB_PREFIX}{job_id}"
            await r.set(key, job.model_dump_json())
        except Exception as e:
            logger.debug(f"Redis complete failed, updated in-memory store for {job_id}: {e}")

        return job

    @staticmethod
    async def fail_job(
        job_id: str,
        error_message: str,
    ) -> Optional[JobStatus]:
        """Mark a job as FAILED with error message."""
        job = await JobManager.get_job(job_id)
        if not job:
            return None

        now = utc_now()
        job.status = JobState.FAILED
        job.error = error_message
        job.progress.status_message = f"Failed: {error_message}"
        job.updated_at = now
        job.completed_at = now

        _in_memory_job_store[job_id] = job

        try:
            r = await get_redis()
            key = f"{settings.REDIS_JOB_PREFIX}{job_id}"
            await r.set(key, job.model_dump_json())
        except Exception as e:
            logger.debug(f"Redis fail failed, updated in-memory store for {job_id}: {e}")

        return job

    @staticmethod
    async def get_job(job_id: str) -> Optional[JobStatus]:
        """Fetch the current status of a job by ID from Redis or in-memory fallback."""
        try:
            r = await get_redis()
            key = f"{settings.REDIS_JOB_PREFIX}{job_id}"
            data = await r.get(key)
            if data:
                return JobStatus.model_validate_json(data)
        except Exception as e:
            logger.debug(f"Redis lookup failed for job {job_id}: {e}")

        # Fallback to in-memory store
        return _in_memory_job_store.get(job_id)
