"""
CodeSentinel Analytics Module: Engineering Intelligence & Metrics Endpoints.
"""

from typing import Any, Dict, List
import uuid
from fastapi import APIRouter
from shared.schemas.common import APIResponse
from app.analytics.engine import AnalyticsEngine
from app.core.envelope import success_response

router = APIRouter()


@router.get(
    "/{project_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Project Intelligence Analytics",
    description="Retrieve comprehensive analytics including transparent health score formula, pass rates by tier, and coverage breakdown.",
)
async def get_analytics(project_id: uuid.UUID) -> APIResponse[Dict[str, Any]]:
    engine = AnalyticsEngine()
    analytics = await engine.get_project_analytics(project_id)
    return success_response(
        data=analytics,
        message="Analytics assembled successfully.",
    )


@router.get(
    "/{project_id}/traceability",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="Get Traceability Matrix",
    description="Assembles Requirement -> Module -> Code -> Test -> Execution -> Result traceability table.",
)
async def get_traceability_matrix(project_id: uuid.UUID) -> APIResponse[List[Dict[str, Any]]]:
    engine = AnalyticsEngine()
    system_model = await engine.client.get_system_model(project_id) or {}
    requirements = system_model.get("requirements", [])
    entities = system_model.get("entities", [])
    tests = await engine.client.get_tests(project_id)
    executions = await engine.client.get_executions(project_id)

    matrix = AnalyticsEngine.build_traceability_matrix(
        requirements=requirements,
        entities=entities,
        test_cases=tests,
        executions=executions,
    )

    return success_response(
        data=matrix,
        message=f"Assembled {len(matrix)} traceability links.",
    )


# ------------------------------------------------------------------------------
# Backward Compatibility Endpoints
# ------------------------------------------------------------------------------

@router.get(
    "/overview/{project_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Engineering Intelligence Overview (Compatibility)",
)
async def get_overview(project_id: uuid.UUID) -> APIResponse[Dict[str, Any]]:
    engine = AnalyticsEngine()
    analytics = await engine.get_project_analytics(project_id)
    health = analytics["health"]
    cov = analytics["coverage"]
    findings = analytics["findings_summary"]

    return success_response(
        data={
            "project_id": str(project_id),
            "health_score": health["health_score"],
            "requirements_verified_pct": cov["requirement_coverage_pct"],
            "code_quality_grade": health["grade"],
            "open_vulnerabilities": findings["by_severity"]["CRITICAL"] + findings["by_severity"]["HIGH"],
            "flaky_tests_count": 0,
            "active_failures": 0,
        },
        message="Analytics overview retrieved.",
    )


@router.get(
    "/metrics/{project_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Detailed Analytics Metrics (Compatibility)",
)
async def get_metrics(project_id: uuid.UUID) -> APIResponse[Dict[str, Any]]:
    engine = AnalyticsEngine()
    analytics = await engine.get_project_analytics(project_id)
    pass_rates = analytics["pass_rates"]

    return success_response(
        data={
            "project_id": str(project_id),
            "provenance_breakdown": {
                k: v["total_runs"] for k, v in pass_rates["by_provenance"].items()
            },
            "build_pass_rate_pct": pass_rates["overall_pass_rate_pct"],
        },
        message="Detailed analytics metrics retrieved.",
    )


@router.get(
    "/{project_id}/report",
    response_model=APIResponse[Dict[str, Any]],
    summary="Get Project Assurance Intelligence Report",
    description="Generate comprehensive Markdown and structured JSON intelligence report.",
)
async def get_project_report(project_id: uuid.UUID) -> APIResponse[Dict[str, Any]]:
    from app.analytics.reports import ReportGenerator
    generator = ReportGenerator()
    json_report = await generator.generate_json_report(project_id)
    return success_response(
        data=json_report,
        message="Project health report generated successfully.",
    )
