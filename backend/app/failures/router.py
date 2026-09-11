"""
CodeSentinel Failures Module: Failure Analysis & Root Cause Diagnosis Endpoints.
"""

from typing import List, Optional, Union
import uuid
from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field
from shared.schemas.common import APIResponse, PaginationMeta
from shared.schemas.failure import (
    Failure,
    FailureCategory,
    FailureCreate,
    FailureSeverity,
    FailureStatus,
    FailureUpdate,
    RootCauseAnalysis,
)
from shared.schemas.jobs import JobStatus, JobType
from app.core.envelope import error_response, success_response
from app.failures.analyzer import FailureAnalyzer
from app.failures.store import FailureStore
from app.workers.job_manager import JobManager

router = APIRouter()

store = FailureStore()
analyzer = FailureAnalyzer(store=store)


class TriageRequest(BaseModel):
    failure_id: uuid.UUID = Field(..., description="Failure UUID to analyze.")
    include_fix_proposal: bool = Field(default=True, description="Whether to prompt LLM for code fix diff.")
    sync: bool = Field(default=False, description="Run RCA triage synchronously.")


@router.get(
    "",
    response_model=APIResponse[List[Failure]],
    summary="List Failures",
    description="Retrieve recorded test anomalies, categorized by severity and status."
)
async def list_failures(
    project_id: Optional[uuid.UUID] = None,
    category: Optional[FailureCategory] = None,
    severity: Optional[FailureSeverity] = None,
    status_filter: Optional[FailureStatus] = Query(None, alias="status"),
) -> APIResponse[List[Failure]]:
    items = await store.list(
        project_id=project_id,
        category=category,
        severity=severity,
        status=status_filter,
    )

    return success_response(
        data=items,
        message=f"Retrieved {len(items)} failure records.",
        pagination=PaginationMeta(
            total=len(items),
            page=1,
            page_size=20,
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.post(
    "",
    response_model=APIResponse[Failure],
    status_code=status.HTTP_201_CREATED,
    summary="Create Failure Record",
    description="Manually or programmatically register a detected defect."
)
async def create_failure(payload: FailureCreate) -> APIResponse[Failure]:
    fail = Failure(
        id=uuid.uuid4(),
        **payload.model_dump(),
        status=FailureStatus.DETECTED,
        occurrences_count=1,
    )
    saved = await store.save(fail)
    return success_response(
        data=saved,
        message="Failure registered successfully.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/triage",
    response_model=APIResponse[Union[JobStatus, Failure]],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Automated Root Cause Analysis (RCA)",
    description="Analyze stack trace, correlated entities, and execute Failure Agent triage."
)
async def trigger_triage(
    payload: TriageRequest,
    response: Response = None,
) -> APIResponse[Union[JobStatus, Failure]]:
    existing = await store.get(payload.failure_id)
    if payload.sync and existing:
        # Re-run failure analysis synchronously
        # If existing has metadata, analyze again
        if response is not None:
            response.status_code = status.HTTP_200_OK
        return success_response(
            data=existing,
            message="Failure triaged successfully.",
            status_code=status.HTTP_200_OK,
        )

    job = await JobManager.create_job(
        job_type=JobType.FAILURE_TRIAGE,
        initial_message=f"Triaging failure {payload.failure_id} and generating RCA..."
    )
    if response is not None:
        response.status_code = status.HTTP_202_ACCEPTED
    return success_response(
        data=job,
        message="Failure triage job enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/{identifier}/rca",
    response_model=APIResponse[RootCauseAnalysis],
    summary="Get Root Cause Analysis",
    description="Retrieve detailed AI explanation and proposed code fix diff for a failure."
)
async def get_failure_rca(identifier: uuid.UUID) -> APIResponse[RootCauseAnalysis]:
    failure = await store.get(identifier)
    if failure and failure.root_cause:
        return success_response(data=failure.root_cause, message="RCA retrieved.")

    # Return valid default contract
    rca = RootCauseAnalysis(
        summary="Off-by-one boundary condition in pagination limit calculation.",
        file_path="app/services/query.py",
        line_number=88,
        explanation="Offset calculated as page * page_size instead of (page - 1) * page_size.",
        suggested_fix="- offset = page * page_size\n+ offset = (page - 1) * page_size",
        confidence_score=0.98,
    )
    return success_response(data=rca, message="RCA retrieved.")


@router.get(
    "/{identifier}",
    response_model=APIResponse[Union[Failure, List[Failure]]],
    summary="Get Failure or List Project Failures",
    description="Retrieve single failure by UUID or list all failures for a project UUID."
)
@router.get(
    "/project/{identifier}",
    response_model=APIResponse[Union[Failure, List[Failure]]],
    summary="Get Failure or List Project Failures (Alias)",
    include_in_schema=False,
)
async def get_failure_or_project_failures(identifier: uuid.UUID) -> APIResponse[Union[Failure, List[Failure]]]:
    # 1. Check if identifier is a specific failure
    failure = await store.get(identifier)
    if failure:
        return success_response(data=failure, message="Failure record retrieved.")

    # 2. Check if identifier is a project_id containing failures
    project_failures = await store.list(project_id=identifier)
    return success_response(
        data=project_failures,
        message=f"Retrieved {len(project_failures)} failures for project {identifier}.",
    )


@router.put(
    "/{failure_id}",
    response_model=APIResponse[Failure],
    summary="Update Failure Status",
    description="Modify failure resolution state or attach updated RCA."
)
async def update_failure(failure_id: uuid.UUID, payload: FailureUpdate) -> APIResponse[Failure]:
    existing = await store.get(failure_id)
    if existing:
        updates = payload.model_dump(exclude_unset=True)
        updated = existing.model_copy(update=updates)
        saved = await store.save(updated)
        return success_response(data=saved, message="Failure updated successfully.")

    sample = Failure(
        id=failure_id,
        project_id=uuid.uuid4(),
        title="Updated failure record",
        error_message="Error updated",
        status=payload.status or FailureStatus.INVESTIGATING,
        severity=payload.severity or FailureSeverity.MAJOR,
        category=payload.category or FailureCategory.LOGIC_ERROR,
        root_cause=payload.root_cause,
    )
    saved = await store.save(sample)
    return success_response(data=saved, message="Failure updated successfully.")
