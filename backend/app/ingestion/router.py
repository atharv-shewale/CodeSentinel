"""
CodeSentinel Ingestion Module: Repositories & Ingestion Endpoints.

Handles repository ingestion triggers (GitHub and ZIP upload), file upload endpoints,
service health queries, and asynchronous job dispatching.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, Optional
import uuid
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from shared.schemas.common import APIResponse, utc_now
from shared.schemas.jobs import JobStatus, JobType
from shared.schemas.project import Project, RepoProvider
from app.core.envelope import error_response, success_response
from app.core.project_store import ProjectStore
from app.ingestion.schemas import IngestRepoRequest, IngestionSourceType
from app.ingestion.service import IngestionService
from app.workers.job_manager import JobManager

router = APIRouter()


@router.post(
    "",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Acquire and Ingest Repository",
    description=(
        "Enqueue repository acquisition (GitHub clone or ZIP extraction) and deep profiling. "
        "Returns a background job_id immediately without blocking."
    ),
)
@router.post(
    "/ingest",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Repository (Alias)",
    description="Backward-compatible alias for /api/v1/repositories.",
    include_in_schema=False,
)
async def ingest_repository(payload: IngestRepoRequest) -> APIResponse[JobStatus]:
    """
    Accept GitHub URL or ZIP upload reference and enqueue asynchronous profiling.
    """
    job = await IngestionService.start_ingestion_job(payload)
    return success_response(
        data=job,
        message="Repository acquisition and profiling job successfully queued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post(
    "/upload",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and Ingest ZIP Archive",
    description="Upload a ZIP archive file directly to initiate sandboxed extraction and profiling.",
)
async def upload_zip_repository(
    file: UploadFile = File(..., description="ZIP archive file of the repository."),
    project_name: Optional[str] = Form(None, description="Optional project name override."),
) -> APIResponse[JobStatus]:
    """Upload a ZIP archive and launch ingestion job."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        return error_response(
            code="INVALID_FILE_TYPE",
            message="Only .zip archive uploads are supported.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Save uploaded file safely to temp directory
    file_id = str(uuid.uuid4())
    temp_zip_path = os.path.join(tempfile.gettempdir(), f"{file_id}.zip")

    try:
        with open(temp_zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        return error_response(
            code="FILE_SAVE_FAILED",
            message=f"Failed to save uploaded file: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    req = IngestRepoRequest(
        source_type=IngestionSourceType.ZIP,
        file_id=file_id,
        project_name=project_name or os.path.splitext(file.filename)[0],
    )
    job = await IngestionService.start_ingestion_job(req)

    return success_response(
        data=job,
        message="ZIP file uploaded and ingestion job enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Ingestion Service Status",
    description="Query Git and ZIP ingestion service health, active jobs, and supported providers.",
)
async def get_ingestion_status() -> APIResponse[Dict[str, Any]]:
    return success_response(
        data={
            "status": "READY",
            "supported_providers": ["GITHUB", "GITLAB", "BITBUCKET", "LOCAL"],
            "max_file_count_limit": 10000,
            "max_repo_size_bytes": 104857600,
            "timestamp": utc_now().isoformat(),
        },
        message="Ingestion service operational.",
    )


@router.post(
    "/sync",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync Repository Changes",
    description="Trigger an incremental git pull and diff analysis for an onboarded project.",
)
async def sync_repository(project_id: uuid.UUID) -> APIResponse[JobStatus]:
    project = await ProjectStore.get(project_id)
    if not project:
        return error_response(
            code="PROJECT_NOT_FOUND",
            message=f"No project found with ID '{project_id}'.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    req = IngestRepoRequest(
        source_type=IngestionSourceType.GITHUB if project.provider == RepoProvider.GITHUB else IngestionSourceType.LOCAL,
        source=project.repository_url,
        branch=project.default_branch,
        project_name=project.name,
    )
    job = await IngestionService.start_ingestion_job(req)

    return success_response(
        data=job,
        message=f"Sync job enqueued for project '{project.name}'.",
        status_code=status.HTTP_202_ACCEPTED,
    )
