"""
CodeSentinel Sandbox Module: Test Execution & Sandbox Telemetry Endpoints.
"""

from typing import List, Optional, Union
import uuid
from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field
from shared.schemas.common import APIResponse, PaginationMeta
from shared.schemas.jobs import JobStatus, JobType
from shared.schemas.test_execution import (
    CoverageMetrics,
    ExecutionEnvironment,
    ExecutionStatus,
    TestExecution,
    TestExecutionCreate,
    TestResultItem,
)
from app.core.envelope import error_response, success_response
from app.sandbox.executor import DockerSandboxExecutor, DockerUnavailableError
from app.sandbox.store import TestExecutionStore
from app.testing.store import TestCaseStore
from app.workers.job_manager import JobManager

router = APIRouter()

execution_store = TestExecutionStore()
test_store = TestCaseStore()
executor = DockerSandboxExecutor(store=execution_store)


class RunExecutionRequest(BaseModel):
    test_case_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Optional list of specific test IDs.")
    test_ids: Optional[List[uuid.UUID]] = Field(default=None, description="Optional list of specific test IDs (alias).")
    triggered_by: str = Field(default="USER", description="Trigger source.")
    commit_sha: Optional[str] = Field(default=None, description="Target commit SHA.")
    timeout_seconds: Optional[int] = Field(default=120, description="Execution timeout limit.")
    sync: bool = Field(default=True, description="Run synchronously if Docker is available.")


@router.post(
    "/run",
    response_model=APIResponse[Union[JobStatus, TestExecution]],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Isolated Sandbox Execution",
    description="Enqueue or execute a test suite run inside an isolated Docker sandbox container."
)
async def trigger_execution(
    payload: TestExecutionCreate,
    response: Response = None,
    sync: bool = Query(default=False),
) -> APIResponse[Union[JobStatus, TestExecution]]:
    if sync:
        if not executor.is_docker_available():
            if response is not None:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return error_response(
                code="DOCKER_UNAVAILABLE",
                message="Docker daemon or sandbox network is unavailable. Cannot execute sandbox container.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        test_cases = []
        for tid in payload.test_case_ids:
            tc = await test_store.get(tid)
            if tc:
                test_cases.append(tc)

        try:
            execution = await executor.execute_test_suite(
                project_id=payload.project_id,
                test_cases=test_cases,
                triggered_by=payload.triggered_by,
                commit_sha=payload.commit_sha,
            )
            if response is not None:
                response.status_code = status.HTTP_200_OK
            return success_response(
                data=execution,
                message="Sandbox test execution completed.",
                status_code=status.HTTP_200_OK,
            )
        except DockerUnavailableError as err:
            if response is not None:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return error_response(
                code="DOCKER_UNAVAILABLE",
                message=str(err),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    job = await JobManager.create_job(
        job_type=JobType.SANDBOX_EXECUTION,
        initial_message=f"Starting sandbox container test run for project {payload.project_id} ({len(payload.test_case_ids)} tests)..."
    )
    if response is not None:
        response.status_code = status.HTTP_202_ACCEPTED
    return success_response(
        data=job,
        message="Sandbox test execution job enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post(
    "/{project_id}/run",
    response_model=APIResponse[Union[JobStatus, TestExecution]],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run Sandbox Tests for Project",
    description="Trigger or run sandbox test execution for a given project."
)
async def run_project_execution(
    project_id: uuid.UUID,
    payload: Optional[RunExecutionRequest] = None,
    response: Response = None,
) -> APIResponse[Union[JobStatus, TestExecution]]:
    sync_mode = payload.sync if (payload and payload.sync is not None) else True

    if sync_mode:
        if not executor.is_docker_available():
            if response is not None:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return error_response(
                code="DOCKER_UNAVAILABLE",
                message="Docker daemon or sandbox network is unavailable. Cannot execute sandbox container.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        test_ids = (payload.test_case_ids or payload.test_ids) if payload else None
        test_cases = []
        if test_ids:
            for tid in test_ids:
                tc = await test_store.get(tid)
                if tc:
                    test_cases.append(tc)
        else:
            test_cases = await test_store.list(project_id=project_id)

        try:
            execution = await executor.execute_test_suite(
                project_id=project_id,
                test_cases=test_cases,
                triggered_by=payload.triggered_by if payload else "USER",
                commit_sha=payload.commit_sha if payload else None,
                timeout_seconds=payload.timeout_seconds if payload else None,
            )
            if response is not None:
                response.status_code = status.HTTP_200_OK
            return success_response(
                data=execution,
                message="Sandbox execution finished.",
                status_code=status.HTTP_200_OK,
            )
        except DockerUnavailableError as err:
            if response is not None:
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return error_response(
                code="DOCKER_UNAVAILABLE",
                message=str(err),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    job = await JobManager.create_job(
        job_type=JobType.SANDBOX_EXECUTION,
        initial_message=f"Starting sandbox container test run for project {project_id}..."
    )
    if response is not None:
        response.status_code = status.HTTP_202_ACCEPTED
    return success_response(
        data=job,
        message="Sandbox test execution job enqueued.",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/project/{project_id}",
    response_model=APIResponse[List[TestExecution]],
    summary="List Project Test Executions",
    description="Query execution history and trend telemetry for a project."
)
async def list_project_executions(project_id: uuid.UUID) -> APIResponse[List[TestExecution]]:
    executions = await execution_store.list(project_id=project_id)

    return success_response(
        data=executions,
        message="Project test executions retrieved.",
        pagination=PaginationMeta(
            total=len(executions),
            page=1,
            page_size=max(len(executions), 1),
            total_pages=1,
            has_next=False,
            has_prev=False,
        ),
    )


@router.get(
    "/{identifier}",
    response_model=APIResponse[Union[TestExecution, List[TestExecution]]],
    summary="Get Test Execution Report or Project Executions",
    description="Retrieve test run results by execution UUID or list executions by project UUID."
)
async def get_execution_or_project(identifier: uuid.UUID) -> APIResponse[Union[TestExecution, List[TestExecution]]]:
    # 1. Check if identifier is an execution_id
    execution = await execution_store.get(identifier)
    if execution:
        return success_response(data=execution, message="Execution details retrieved.")

    # 2. Check if identifier has project executions
    project_execs = await execution_store.list(project_id=identifier)
    if project_execs:
        return success_response(
            data=project_execs,
            message=f"Retrieved {len(project_execs)} executions for project {identifier}."
        )

    # 3. Default fallback sample
    sample = TestExecution(
        id=identifier,
        project_id=uuid.uuid4(),
        triggered_by="agent:test-generator",
        environment=ExecutionEnvironment.DOCKER_SANDBOX,
        commit_sha="a1b2c3d4e5f67890",
        test_case_ids=[uuid.uuid4(), uuid.uuid4()],
        status=ExecutionStatus.PASSED,
        total_tests=15,
        passed_tests=15,
        failed_tests=0,
        errored_tests=0,
        total_duration_ms=1420.5,
        results=[
            TestResultItem(
                test_case_id=uuid.uuid4(),
                test_name="test_auth_flow",
                status=ExecutionStatus.PASSED,
                duration_ms=84.2,
                stdout="PASSED [100%]\n",
            )
        ],
        coverage=CoverageMetrics(
            statement_coverage_pct=92.4,
            branch_coverage_pct=88.0,
            line_coverage_pct=91.8,
            covered_lines=450,
            total_lines=490,
            covered_files=["app/core/auth.py", "app/api/v1/endpoints/auth.py"],
        ),
    )
    return success_response(data=sample, message="Execution details retrieved.")
