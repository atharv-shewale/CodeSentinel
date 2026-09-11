"""
CodeSentinel Analyzer: Analysis API Endpoints.

Provides deep AST analysis triggers, entity inspection, and Software System Model retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from shared.schemas.code_entity import CodeEntity, CodeLocation, EntityType
from shared.schemas.common import APIResponse, utc_now
from shared.schemas.jobs import JobStatus
from app.analyzer.service import CodeAnalyzerService
from app.analyzer.store import AnalysisStore
from app.analyzer.system_model import SoftwareSystemModel, SystemModelStore
from app.core.envelope import error_response, success_response
from app.core.project_store import ProjectStore

router = APIRouter()


class AnalysisTriggerRequest(BaseModel):
    project_id: uuid.UUID = Field(..., description="Project UUID to analyze.")
    root_dir: Optional[str] = Field(default=None, description="Optional local directory path for code scanning.")
    project_name: Optional[str] = Field(default=None, description="Optional project name.")


@router.post(
    "",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Deep Code Analysis",
    description="Enqueue AST analysis, function-call resolution, and system model assembly.",
)
@router.post(
    "/ast",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AST Analysis (Alias)",
    include_in_schema=False,
)
async def trigger_code_analysis(payload: AnalysisTriggerRequest) -> APIResponse[JobStatus]:
    """Enqueue deep AST code analysis."""
    # Attempt to fetch project metadata from ProjectStore if root_dir not supplied
    project = await ProjectStore.get(payload.project_id)
    project_name = payload.project_name or (project.name if project else f"Project-{str(payload.project_id)[:8]}")
    root_dir = payload.root_dir or (project.metadata.get("root_dir") if project and project.metadata else None)

    job = await CodeAnalyzerService.start_analysis_job(
        project_id=payload.project_id,
        root_dir=root_dir,
        project_name=project_name,
    )
    return success_response(
        data=job,
        message="Code analysis and AST extraction job enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/entities/{project_id}",
    response_model=APIResponse[List[CodeEntity]],
    summary="Get Analyzed Code Entities",
    description="Retrieve list of extracted CodeEntity objects for a project.",
)
async def get_project_entities(project_id: uuid.UUID) -> APIResponse[List[CodeEntity]]:
    """Retrieve code entities from PostgreSQL or return default sample."""
    entities = await AnalysisStore.get(project_id)
    if entities:
        return success_response(
            data=entities,
            message=f"Retrieved {len(entities)} code entities.",
        )

    # Return sample entities for unanalyzed project
    now = utc_now()
    sample = CodeEntity(
        id=uuid.uuid4(),
        project_id=project_id,
        name="UserService",
        qualified_name="app.services.user.UserService",
        entity_type=EntityType.CLASS,
        language="python",
        location=CodeLocation(file_path="app/services/user.py", start_line=10, end_line=45),
        created_at=now,
        updated_at=now,
    )
    return success_response(data=[sample], message="Sample entity returned.")


@router.get(
    "/routes/{project_id}",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Get Extracted Routes",
    description="Retrieve HTTP routes extracted during analysis or profile cross-referencing.",
)
async def get_project_routes(project_id: uuid.UUID) -> APIResponse[List[Dict[str, Any]]]:
    """Retrieve discovered HTTP routes."""
    project = await ProjectStore.get(project_id)
    apis = project.metadata.get("apis", []) if project else []
    if not apis:
        apis = [{"method": "GET", "path": "/api/v1/users", "framework": "FastAPI"}]

    return success_response(
        data=apis,
        message=f"Retrieved {len(apis)} API routes.",
    )


@router.get(
    "/{project_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Analysis Summary",
    description="Retrieve extracted code entity summary and class/function metrics.",
)
async def get_analysis_summary(project_id: uuid.UUID) -> APIResponse[Dict[str, Any]]:
    """Retrieve code analysis status and summary counts."""
    entities = await AnalysisStore.get(project_id)
    if not entities:
        return success_response(
            data={
                "project_id": str(project_id),
                "status": "READY",
                "total_entities": 0,
                "total_classes": 0,
                "total_functions": 0,
                "entities": [],
            },
            message="No code analysis recorded for this project yet.",
        )

    classes_count = sum(1 for e in entities if e.entity_type.value == "CLASS")
    funcs_count = sum(1 for e in entities if e.entity_type.value in ("FUNCTION", "METHOD"))

    return success_response(
        data={
            "project_id": str(project_id),
            "status": "READY",
            "total_entities": len(entities),
            "total_classes": classes_count,
            "total_functions": funcs_count,
            "entities": [e.model_dump(mode="json") for e in entities],
        },
        message=f"Retrieved {len(entities)} analyzed code entities.",
    )


@router.get(
    "/{project_id}/system-model",
    response_model=APIResponse[SoftwareSystemModel],
    summary="Get Software System Model",
    description=(
        "Retrieve the assembled project-wide Software System Model representing "
        "files -> classes -> functions -> APIs -> dependencies -> requirements -> code links."
    ),
)
async def get_system_model(project_id: uuid.UUID) -> APIResponse[SoftwareSystemModel]:
    """Retrieve or assemble the complete Software System Model for Module 3 (Neo4j)."""
    existing_model = await SystemModelStore.get(project_id)
    if existing_model:
        return success_response(
            data=existing_model,
            message="Software System Model retrieved from database.",
        )

    project = await ProjectStore.get(project_id)
    project_name = project.name if project else f"Project-{str(project_id)[:8]}"
    profile_metadata = project.metadata if project else None
    root_dir = profile_metadata.get("root_dir") if profile_metadata else None

    assembled_model = await CodeAnalyzerService.run_analysis(
        project_id=project_id,
        root_dir=root_dir,
        project_name=project_name,
        profile_metadata=profile_metadata,
    )

    return success_response(
        data=assembled_model,
        message="Software System Model successfully assembled.",
    )
