"""
CodeSentinel Jobs API Endpoints.

Provides status polling and test job dispatch for asynchronous background operations.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from shared.schemas.common import APIResponse
from shared.schemas.jobs import JobStatus, JobType
from app.core.envelope import error_response, success_response
from app.workers.job_manager import JobManager

router = APIRouter()


class CreateTestJobRequest(BaseModel):
    job_type: JobType = Field(default=JobType.AST_ANALYSIS, description="Type of job to test.")
    total_steps: int = Field(default=10, description="Step count for test simulation.")


@router.get(
    "/{job_id}",
    response_model=APIResponse[JobStatus],
    summary="Get Background Job Status",
    description="Poll real-time progress, lifecycle state, error message, or result payload for a background task."
)
async def get_job_status(job_id: str) -> APIResponse[JobStatus]:
    job = await JobManager.get_job(job_id)
    if not job:
        # Return structured 404 error envelope
        return error_response(
            code="JOB_NOT_FOUND",
            message=f"No background job found with ID '{job_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return success_response(
        data=job,
        message=f"Job status is {job.status.value} ({job.progress.percentage}% complete)."
    )


@router.post(
    "/test-job",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dispatch Test Job",
    description="Enqueue a test background task to verify Redis queue and worker processing."
)
async def dispatch_test_job(payload: CreateTestJobRequest) -> APIResponse[JobStatus]:
    job = await JobManager.create_job(
        job_type=payload.job_type,
        total_steps=payload.total_steps,
        initial_message="Test background job queued for worker processing."
    )
    return success_response(
        data=job,
        message="Test job successfully enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )
