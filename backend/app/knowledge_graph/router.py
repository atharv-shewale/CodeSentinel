"""
CodeSentinel Knowledge Graph Module: REST API Endpoints.

Provides:
- POST /api/v1/knowledge/{project_id}/build: Background task triggering graph materialization.
- GET /api/v1/knowledge/{project_id}/query: Executes one of 4 named query types (NO raw Cypher).
- GET /api/v1/knowledge/graph/{project_id}: Retrieves the complete graph topology.
- POST /api/v1/knowledge/query: Legacy endpoint compatibility.
"""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from shared.schemas.common import APIResponse
from shared.schemas.jobs import JobStatus, JobType
from app.core.envelope import error_response, success_response
from app.knowledge_graph.models import (
    GraphResponse,
    GraphTopologyResponse,
    KnowledgeQueryType,
)
from app.knowledge_graph.service import KnowledgeGraphService
from app.workers.job_manager import JobManager

router = APIRouter()


class GraphQueryRequest(BaseModel):
    project_id: uuid.UUID = Field(..., description="Project UUID.")
    query_type: Optional[KnowledgeQueryType] = Field(
        default=KnowledgeQueryType.UNTESTED_REQUIREMENTS,
        description="Named query traversal type."
    )
    function_name: Optional[str] = Field(default=None, description="Target function name for call neighborhood.")
    failure_id: Optional[str] = Field(default=None, description="Target failure UUID for failure analysis.")
    commit_hash: Optional[str] = Field(default=None, description="Target commit hash for commit impact.")
    depth: int = Field(default=1, ge=1, le=5, description="Graph traversal depth.")
    cypher_query: Optional[str] = Field(default=None, description="Ignored: Raw Cypher execution is strictly prohibited.")


@router.post(
    "/{project_id}/build",
    response_model=APIResponse[JobStatus],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Build Project Knowledge Graph",
    description="Trigger asynchronous graph loading job to materialize the Software System Model into Neo4j with full re-index policy."
)
async def build_project_knowledge_graph(project_id: uuid.UUID) -> APIResponse[JobStatus]:
    """Trigger background job to build or refresh the project knowledge graph."""
    job = await JobManager.create_job(
        job_type=JobType.KNOWLEDGE_GRAPH_BUILD,
        initial_message=f"Building Neo4j knowledge graph for project {project_id}..."
    )

    # Trigger graph build immediately in service
    try:
        await KnowledgeGraphService.build_graph_for_project(project_id)
        completed_job = await JobManager.complete_job(
            job_id=job.job_id,
            message="Knowledge graph built successfully."
        )
        return success_response(
            data=completed_job or job,
            message="Knowledge graph build job completed.",
            status_code=status.HTTP_202_ACCEPTED,
        )
    except Exception as e:
        failed_job = await JobManager.fail_job(
            job_id=job.job_id,
            error_message=f"Failed to build knowledge graph: {str(e)}"
        )
        return success_response(
            data=failed_job or job,
            message="Knowledge graph build failed.",
            status_code=status.HTTP_202_ACCEPTED,
        )


@router.get(
    "/{project_id}/query",
    response_model=APIResponse[Dict[str, Any]],
    summary="Execute Named Knowledge Graph Query",
    description="Execute one of 4 predefined graph traversal queries. Arbitrary Cypher is strictly rejected."
)
async def query_knowledge_graph_by_type(
    project_id: uuid.UUID,
    query_type: KnowledgeQueryType = Query(..., description="Named query type (untested_requirements, failure_functions, commit_impact, call_neighborhood)"),
    function_name: Optional[str] = Query(None, description="Function name or qualified name for call_neighborhood query"),
    failure_id: Optional[str] = Query(None, description="Failure UUID for failure_functions query"),
    commit_hash: Optional[str] = Query(None, description="Commit hash for commit_impact query"),
    depth: int = Query(1, ge=1, le=5, description="Traversal depth"),
) -> APIResponse[Dict[str, Any]]:
    """Execute named graph traversal queries with validation."""
    pid_str = str(project_id)
    topo = await KnowledgeGraphService.get_project_topology(project_id)
    if topo.total_nodes == 0:
        return error_response(
            code="GRAPH_NOT_INITIALIZED",
            message=f"No knowledge graph data loaded for project {pid_str}. Please run POST /api/v1/knowledge/{pid_str}/build first.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if query_type == KnowledgeQueryType.UNTESTED_REQUIREMENTS:
        results = await KnowledgeGraphService.get_untested_requirements(project_id)
        return success_response(
            data={
                "project_id": pid_str,
                "query_type": query_type.value,
                "total_results": len(results),
                "untested_requirements": [r.model_dump(mode="json") for r in results],
            },
            message=f"Found {len(results)} requirements with no linked tests."
        )

    elif query_type == KnowledgeQueryType.FAILURE_FUNCTIONS:
        results = await KnowledgeGraphService.get_failure_related_functions(project_id, failure_id=failure_id)
        return success_response(
            data={
                "project_id": pid_str,
                "query_type": query_type.value,
                "total_results": len(results),
                "failures": [r.model_dump(mode="json") for r in results],
            },
            message=f"Found {len(results)} failure-to-function correlation records."
        )

    elif query_type == KnowledgeQueryType.COMMIT_IMPACT:
        results = await KnowledgeGraphService.get_commit_impact_and_tests(project_id, commit_hash=commit_hash)
        return success_response(
            data={
                "project_id": pid_str,
                "query_type": query_type.value,
                "total_results": len(results),
                "commit_impacts": [r.model_dump(mode="json") for r in results],
            },
            message=f"Found {len(results)} commit impact records."
        )

    elif query_type == KnowledgeQueryType.CALL_NEIGHBORHOOD:
        if not function_name:
            return error_response(
                code="MISSING_PARAMETER",
                message="Parameter 'function_name' is required for call_neighborhood query.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        results = await KnowledgeGraphService.get_call_neighborhood(project_id, function_name=function_name, depth=depth)
        return success_response(
            data={
                "project_id": pid_str,
                "query_type": query_type.value,
                "total_results": len(results),
                "call_neighborhoods": [r.model_dump(mode="json") for r in results],
            },
            message=f"Retrieved call graph neighborhood for '{function_name}'."
        )

    return error_response(
        code="INVALID_QUERY_TYPE",
        message=f"Unsupported query type '{query_type}'.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@router.get(
    "/graph/{project_id}",
    response_model=APIResponse[GraphTopologyResponse],
    summary="Get Project Knowledge Graph Topology",
    description="Retrieve code architecture knowledge graph nodes (classes, functions, endpoints) and relationship edges."
)
async def get_project_knowledge_graph(project_id: uuid.UUID) -> APIResponse[GraphTopologyResponse]:
    """Retrieve full knowledge graph topology."""
    topo = await KnowledgeGraphService.get_project_topology(project_id)
    return success_response(
        data=topo,
        message=f"Knowledge graph topology retrieved ({topo.total_nodes} nodes, {topo.total_edges} edges)."
    )


@router.post(
    "/query",
    response_model=APIResponse[Dict[str, Any]],
    summary="Execute Knowledge Graph Query",
    description="Execute structured relational queries over Neo4j knowledge graph (rejects arbitrary Cypher)."
)
async def query_knowledge_graph(payload: GraphQueryRequest) -> APIResponse[Dict[str, Any]]:
    """Legacy route compatibility mapping to named query types."""
    q_type = payload.query_type or KnowledgeQueryType.UNTESTED_REQUIREMENTS
    return await query_knowledge_graph_by_type(
        project_id=payload.project_id,
        query_type=q_type,
        function_name=payload.function_name,
        failure_id=payload.failure_id,
        commit_hash=payload.commit_hash,
        depth=payload.depth,
    )
