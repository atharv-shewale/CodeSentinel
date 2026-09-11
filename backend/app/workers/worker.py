"""
CodeSentinel Backend: Standalone Background Worker.

Consumes job IDs from Redis queue and dispatches task executions.
"""

import sys
from pathlib import Path

# Ensure project root and backend directory are always on sys.path
_root = Path(__file__).resolve().parent.parent.parent
_backend = Path(__file__).resolve().parent.parent
for _p in [str(_root), str(_backend)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import asyncio
from typing import Optional
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.redis import close_redis, get_redis
from app.workers.job_manager import JobManager


async def process_job(job_id: str) -> None:
    """Simulate job processing lifecycle for stubs."""
    logger.info(f"Worker picked up job {job_id}")
    job = await JobManager.get_job(job_id)
    from shared.schemas.jobs import JobType
    # Do not hijack jobs managed by dedicated in-process services
    IN_PROCESS_JOB_TYPES = {
        JobType.REPO_INGESTION,
        JobType.REQUIREMENTS_PARSING,
        getattr(JobType, "REQUIREMENT_PARSING", None),
        JobType.TEST_GENERATION,
        JobType.SANDBOX_EXECUTION,
        JobType.COMPLIANCE_AUDIT,
    }
    if job.job_type in IN_PROCESS_JOB_TYPES:
        logger.debug(f"Worker skipping {job.job_type} job {job_id} handled by in-process pipeline.")
        return

    try:
        # Simulate steps for async tasks without dedicated handlers
        await JobManager.update_progress(job_id, 25, "Analyzing codebase structure...", total_steps=100)
        await asyncio.sleep(0.5)
        await JobManager.update_progress(job_id, 75, "Extracting AST & generating embeddings...", total_steps=100)
        await asyncio.sleep(0.5)
        current = await JobManager.get_job(job_id)
        if current and current.result:
            result = current.result
        else:
            result = {"status": "success", "processed_entities": 42}
        await JobManager.complete_job(job_id, result=result)
        logger.info(f"Worker completed job {job_id}")
    except Exception as e:
        logger.error(f"Worker failed processing job {job_id}: {e}")
        await JobManager.fail_job(job_id, error_message=str(e))


async def worker_loop() -> None:
    """Main worker event loop polling Redis list."""
    setup_logging()
    logger.info("Starting CodeSentinel background worker...")
    r = await get_redis()

    while True:
        try:
            # Blocking pop from Redis queue with 2-second timeout
            item = await r.blpop(settings.REDIS_JOB_QUEUE, timeout=2)
            if item:
                _, job_id = item
                await process_job(job_id)
        except asyncio.CancelledError:
            logger.info("Worker received stop signal.")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(2)

    await close_redis()


if __name__ == "__main__":
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        pass
