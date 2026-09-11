"""
CodeSentinel Background Job Manager Tests.

Validates job creation, step progress updates, completion, failure handling,
and retrieval logic.
"""

import pytest
from shared.schemas.jobs import JobState, JobType
from app.workers.job_manager import JobManager


@pytest.mark.asyncio
async def test_job_lifecycle_state_machine():
    """Verify JobManager lifecycle transitions."""
    # 1. Create Job
    job = await JobManager.create_job(
        job_type=JobType.AST_ANALYSIS,
        total_steps=50,
        initial_message="Starting AST extraction..."
    )
    job_id = job.job_id
    assert job.status == JobState.PENDING
    assert job.progress.percentage == 0.0

    # 2. Update Progress
    updated_job = await JobManager.update_progress(
        job_id=job_id,
        current_step=25,
        status_message="Parsed 25 AST files..."
    )
    assert updated_job is not None
    assert updated_job.status == JobState.RUNNING
    assert updated_job.progress.current_step == 25
    assert updated_job.progress.percentage == 50.0

    # 3. Complete Job
    completed_job = await JobManager.complete_job(
        job_id=job_id,
        result={"extracted_functions": 120, "classes": 18}
    )
    assert completed_job is not None
    assert completed_job.status == JobState.COMPLETED
    assert completed_job.progress.percentage == 100.0
    assert completed_job.result["extracted_functions"] == 120
    assert completed_job.completed_at is not None


@pytest.mark.asyncio
async def test_job_failure_transition():
    """Verify JobManager error and failure transition."""
    job = await JobManager.create_job(job_type=JobType.SANDBOX_EXECUTION)
    job_id = job.job_id

    failed_job = await JobManager.fail_job(
        job_id=job_id,
        error_message="Docker sandbox container OOM killed."
    )
    assert failed_job is not None
    assert failed_job.status == JobState.FAILED
    assert failed_job.error == "Docker sandbox container OOM killed."
    assert failed_job.completed_at is not None
