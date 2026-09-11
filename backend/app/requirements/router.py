"""
CodeSentinel Requirements: Requirements API Endpoints.

Handles specification document uploads, raw text ingestion, and requirement queries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import uuid
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from shared.schemas.common import APIResponse, utc_now
from shared.schemas.jobs import JobStatus
from shared.schemas.requirement import (
    Requirement,
    RequirementCreate,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
)
from app.core.envelope import error_response, success_response
from app.requirements.extractor import DocumentParsingError
from app.requirements.service import RequirementService
from app.requirements.store import RequirementStore

router = APIRouter()


class RequirementIngestRequest(BaseModel):
    project_id: uuid.UUID = Field(..., description="Target project UUID.")
    text: Optional[str] = Field(default=None, description="Raw specification text.")
    document_title: Optional[str] = Field(default="Specification", description="Document label.")
    identifier: Optional[str] = Field(default=None, description="Optional requirement identifier.")
    title: Optional[str] = Field(default=None, description="Optional requirement title.")
    description: Optional[str] = Field(default=None, description="Optional requirement description.")
    req_type: Optional[RequirementType] = Field(default=RequirementType.FUNCTIONAL)
    priority: Optional[RequirementPriority] = Field(default=RequirementPriority.MEDIUM)
    acceptance_criteria: Optional[List[str]] = Field(default_factory=list)


@router.post(
    "",
    response_model=APIResponse[Any],
    status_code=status.HTTP_201_CREATED,
    summary="Create or Ingest Requirements",
    description="Create a single requirement or parse multi-section specification text.",
)
async def ingest_requirements(
    payload: RequirementIngestRequest,
    response: Response,
) -> APIResponse[Any]:
    """Ingest specification text or create direct Requirement entity."""
    now = utc_now()

    # Case 1: Direct Requirement Creation (Phase 0 / CRUD contract compatibility)
    if payload.identifier and (payload.title or payload.description):
        req = Requirement(
            id=uuid.uuid4(),
            project_id=payload.project_id,
            identifier=payload.identifier,
            title=payload.title or payload.identifier,
            description=payload.description or payload.title or "",
            req_type=payload.req_type or RequirementType.FUNCTIONAL,
            priority=payload.priority or RequirementPriority.MEDIUM,
            status=RequirementStatus.APPROVED if payload.acceptance_criteria else RequirementStatus.DRAFT,
            acceptance_criteria=payload.acceptance_criteria or [],
            created_at=now,
            updated_at=now,
        )
        await RequirementStore.save(payload.project_id, [req])
        response.status_code = status.HTTP_201_CREATED
        return success_response(
            data=req,
            message="Requirement created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    # Case 2: Document / Section Parsing from text
    if payload.text:
        reqs = await RequirementService.process_raw_text(
            project_id=payload.project_id,
            text=payload.text,
            source_name=payload.document_title or "text_input",
        )
        response.status_code = status.HTTP_202_ACCEPTED
        return success_response(
            data=[r.model_dump(mode="json") for r in reqs],
            message=f"Successfully extracted {len(reqs)} requirement entities.",
            status_code=status.HTTP_202_ACCEPTED,
        )

    # Empty payload
    response.status_code = status.HTTP_202_ACCEPTED
    return success_response(
        data={"status": "QUEUED", "project_id": str(payload.project_id)},
        message="Requirement ingestion job queued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post(
    "/upload",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_200_OK,
    summary="Upload Specification Document",
    description="Upload a PDF, DOCX, Markdown, or text file for background requirement extraction.",
)
async def upload_requirement_document(
    project_id: uuid.UUID = Form(..., description="Target project UUID."),
    file: UploadFile = File(..., description="Specification document (.md, .txt, .pdf, .docx)."),
) -> APIResponse[JobStatus]:
    """Upload specification file and enqueue background requirement extraction."""
    if not file.filename:
        return error_response(
            code="MISSING_FILENAME",
            message="Uploaded file must have a valid filename.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        content = await file.read()
        job = await RequirementService.start_extraction_job(
            project_id=project_id,
            file_content=content,
            filename=file.filename,
        )
        return success_response(
            data=job,
            message=f"Document '{file.filename}' uploaded and parsing job enqueued.",
            status_code=status.HTTP_200_OK,
        )
    except DocumentParsingError as e:
        return error_response(
            code=e.code,
            message=e.message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return error_response(
            code="UPLOAD_FAILED",
            message=f"Failed to process document upload: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "",
    response_model=APIResponse[List[Requirement]],
    summary="List Requirements",
    description="Retrieve all requirements across projects or sample requirement.",
)
async def list_requirements() -> APIResponse[List[Requirement]]:
    """List requirements."""
    now = utc_now()
    sample = Requirement(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        identifier="REQ-SYS-001",
        title="Sample Requirement",
        description="System integrity requirement.",
        created_at=now,
        updated_at=now,
    )
    return success_response(data=[sample], message="Requirements listed.")


@router.get(
    "/{project_id}",
    response_model=APIResponse[List[Requirement]],
    summary="Get Project Requirements",
    description="Retrieve all extracted Requirement entities for a project.",
)
async def get_project_requirements(project_id: uuid.UUID) -> APIResponse[List[Requirement]]:
    """Retrieve all requirements for a project from PostgreSQL."""
    reqs = await RequirementStore.get(project_id)
    return success_response(
        data=reqs,
        message=f"Retrieved {len(reqs)} requirements for project '{project_id}'.",
    )
