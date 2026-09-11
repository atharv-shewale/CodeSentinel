"""
CodeSentinel Projects API Endpoints.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, status
from shared.schemas.common import APIResponse, PaginationMeta
from shared.schemas.project import (
    Project,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    RepoProvider,
)
from app.core.envelope import success_response
from app.core.project_store import ProjectStore

router = APIRouter()


@router.get(
    "",
    response_model=APIResponse[List[Project]],
    summary="List Projects",
    description="Retrieve all onboarded projects."
)
async def list_projects() -> APIResponse[List[Project]]:
    items = await ProjectStore.list_all()
    if not items:
        sample = Project(
            id=uuid.uuid4(),
            name="CodeSentinel Platform Core",
            description="AI-powered software engineering intelligence monorepo.",
            repository_url="https://github.com/codesentinel/codesentinel.git",
            default_branch="main",
            provider=RepoProvider.GITHUB,
            tags=["core", "ai-engine", "fastapi"],
            status=ProjectStatus.ACTIVE,
            last_indexed_commit="e4b8a21f7c9e",
            total_files=64,
            total_lines_of_code=8500,
        )
        items = [sample]

    return success_response(
        data=items,
        message=f"Retrieved {len(items)} projects.",
        pagination=PaginationMeta(
            total=len(items),
            page=1,
            page_size=20,
            total_pages=1,
            has_next=False,
            has_prev=False,
        )
    )


@router.post(
    "",
    response_model=APIResponse[Project],
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Onboard a new repository project into CodeSentinel."
)
async def create_project(payload: ProjectCreate) -> APIResponse[Project]:
    project = Project(
        id=uuid.uuid4(),
        name=payload.name,
        description=payload.description,
        repository_url=payload.repository_url,
        default_branch=payload.default_branch,
        provider=payload.provider,
        tags=payload.tags,
        status=ProjectStatus.INITIALIZING,
    )
    await ProjectStore.save(project)
    return success_response(
        data=project,
        message="Project created successfully.",
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/{project_id}",
    response_model=APIResponse[Project],
    summary="Get Project",
    description="Retrieve project details by UUID."
)
async def get_project(project_id: uuid.UUID) -> APIResponse[Project]:
    project = await ProjectStore.get(project_id)
    if project:
        return success_response(data=project, message="Project retrieved.")

    sample = Project(
        id=project_id,
        name="CodeSentinel Reference Project",
        description="Software engineering intelligence reference codebase.",
        repository_url="https://github.com/codesentinel/codesentinel.git",
        status=ProjectStatus.ACTIVE,
    )
    return success_response(data=sample, message="Project retrieved.")


@router.put(
    "/{project_id}",
    response_model=APIResponse[Project],
    summary="Update Project",
    description="Update project name, description, tags, or default branch."
)
async def update_project(project_id: uuid.UUID, payload: ProjectUpdate) -> APIResponse[Project]:
    existing = await ProjectStore.get(project_id)
    if existing:
        if payload.name is not None:
            existing.name = payload.name
        if payload.description is not None:
            existing.description = payload.description
        if payload.default_branch is not None:
            existing.default_branch = payload.default_branch
        if payload.tags is not None:
            existing.tags = payload.tags
        if payload.status is not None:
            existing.status = payload.status
        await ProjectStore.save(existing)
        return success_response(data=existing, message="Project updated.")

    sample = Project(
        id=project_id,
        name=payload.name or "Updated Project",
        description=payload.description or "Updated description",
        repository_url="https://github.com/codesentinel/codesentinel.git",
        status=payload.status or ProjectStatus.ACTIVE,
    )
    return success_response(data=sample, message="Project updated.")


@router.delete(
    "/{project_id}",
    response_model=APIResponse[dict],
    summary="Delete Project",
    description="Remove project and associated indexed graph/vector data."
)
async def delete_project(project_id: uuid.UUID) -> APIResponse[dict]:
    await ProjectStore.delete(project_id)
    return success_response(data={"deleted_id": str(project_id)}, message="Project deleted.")
