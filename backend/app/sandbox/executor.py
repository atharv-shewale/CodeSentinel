"""
CodeSentinel Sandbox Module: Hardened Docker Sandbox Executor.

Executes test suites inside isolated, hardened ephemeral Docker containers.
Guarantees:
- Network isolation (network_mode='none' for test execution stage)
- Read-only root filesystem with scoped tmpfs
- Non-root user execution
- Memory, CPU, and PID resource bounds
- Wall-clock timeout enforcement
- Guaranteed ephemeral container cleanup in try/finally
- Result classification: PASS, FAIL, ERROR, TIMEOUT
- Typed error on Docker daemon / sandbox network unavailability
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from shared.schemas.common import utc_now
from shared.schemas.test_case import TestCase
from shared.schemas.test_execution import (
    ExecutionEnvironment,
    ExecutionStatus,
    TestExecution,
    TestResultItem,
)
from app.core.config import settings
from app.core.logging import logger
from app.sandbox.security import SandboxSecurityProfile
from app.sandbox.store import TestExecutionStore


class DockerUnavailableError(Exception):
    """Raised when the Docker daemon or sandbox network is inaccessible."""
    pass


class DockerSandboxExecutor:
    """Orchestrates secure ephemeral container test execution."""

    def __init__(
        self,
        security_profile: Optional[SandboxSecurityProfile] = None,
        store: Optional[TestExecutionStore] = None,
    ):
        self.profile = security_profile or SandboxSecurityProfile()
        self.profile.validate_security_invariants()
        self.store = store or TestExecutionStore()
        self._docker_client = None

    def _get_docker_client(self):
        """Lazy-initialize Docker client or raise DockerUnavailableError."""
        if self._docker_client is not None:
            return self._docker_client

        try:
            import docker
            client = docker.from_env()
            # Verify connectivity via ping
            client.ping()
            self._docker_client = client
            return self._docker_client
        except Exception as e:
            logger.warning(f"Docker daemon is unavailable: {e}")
            raise DockerUnavailableError(
                f"Docker daemon or sandbox network is unavailable: {e}. "
                "Ensure Docker Desktop/daemon is running."
            ) from e

    def is_docker_available(self) -> bool:
        """Check if real Docker engine is available."""
        try:
            self._get_docker_client()
            return True
        except DockerUnavailableError:
            return False

    @staticmethod
    def classify_result(
        exit_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool = False,
    ) -> Tuple[ExecutionStatus, Optional[str], Optional[str]]:
        """
        Classify test execution outcome into exactly one of:
        PASSED, FAILED, ERROR, TIMED_OUT.

        Semantic Distinction:
        - ERROR: Test failed to even start/load (e.g. missing dependency, syntax error, exit code 2).
        - FAILED: Test ran but failed assertions (AssertionError, exit code 1).
        - PASSED: Clean exit 0.
        - TIMED_OUT: Wall-clock timeout exceeded.
        """
        combined = f"{stdout}\n{stderr}"

        if timed_out:
            return ExecutionStatus.TIMED_OUT, "Execution exceeded hard wall-clock timeout limit.", combined

        # Check for OOM killer / SIGKILL (128 + 9 = 137)
        if exit_code == 137 or "OOMKilled" in combined or "Out of memory" in combined:
            return (
                ExecutionStatus.ERROR,
                f"Container killed: Out of Memory (OOM) or SIGKILL (exit code {exit_code}).",
                combined,
            )

        # Check for startup / dependency / environment errors first
        error_indicators = [
            "ModuleNotFoundError:",
            "ImportError:",
            "SyntaxError:",
            "IndentationError:",
            "No module named",
            "command not found",
            "pytest: error:",
            "usage: pytest",
        ]
        if exit_code == 2 or any(indicator in combined for indicator in error_indicators):
            first_err_line = next((l for l in combined.splitlines() if any(i in l for i in error_indicators)), None)
            return (
                ExecutionStatus.ERROR,
                first_err_line or f"Test failed to start or encountered dependency error (exit code {exit_code}).",
                combined,
            )

        # Check for assertion failure / test failure
        if exit_code == 1 or "AssertionError" in combined or "FAILED" in combined:
            first_fail_line = next((l for l in combined.splitlines() if "AssertionError" in l or "FAILED" in l), None)
            return (
                ExecutionStatus.FAILED,
                first_fail_line or f"Test assertion failed (exit code {exit_code}).",
                combined,
            )

        if exit_code == 0:
            return ExecutionStatus.PASSED, None, None

        # Fallback for other non-zero exits
        return ExecutionStatus.ERROR, f"Non-zero container exit code: {exit_code}", combined

    async def run_single_test_container(
        self,
        test_case: TestCase,
        timeout_seconds: Optional[int] = None,
        docker_image: str = "python:3.12-slim",
    ) -> TestResultItem:
        """
        Execute an individual test in an ephemeral hardened Docker container.
        Guarantees container removal in try/finally.
        """
        client = self._get_docker_client()
        timeout = timeout_seconds or self.profile.default_timeout_seconds
        start_time = time.monotonic()

        # Build inline test script
        test_content = (
            "import sys\n"
            f"{test_case.setup_code or ''}\n"
            f"{test_case.test_code}\n"
            f"if __name__ == '__main__':\n"
            f"    try:\n"
            f"        {test_case.name}()\n"
            f"        sys.exit(0)\n"
            f"    except AssertionError as ae:\n"
            f"        sys.stderr.write(f'AssertionError: {{ae}}\\n')\n"
            f"        sys.exit(1)\n"
            f"    except Exception as e:\n"
            f"        sys.stderr.write(f'{{type(e).__name__}}: {{e}}\\n')\n"
            f"        sys.exit(2)\n"
        )

        container = None
        timed_out = False
        exit_code = 0
        stdout_text = ""
        stderr_text = ""

        try:
            # Stage 2 (Execution): strictly network_mode='none'
            host_config = self.profile.to_docker_host_config(execution_stage="TEST")

            container = client.containers.create(
                image=docker_image,
                command=["python", "-c", test_content],
                user=self.profile.user,
                network_mode=host_config["network_mode"],
                read_only=host_config["read_only"],
                tmpfs=host_config["tmpfs"],
                mem_limit=host_config["mem_limit"],
                memswap_limit=host_config["memswap_limit"],
                nano_cpus=host_config["nano_cpus"],
                pids_limit=host_config["pids_limit"],
                cap_drop=host_config["cap_drop"],
                detach=True,
            )

            container.start()

            # Wait with hard wall-clock timeout
            loop = asyncio.get_running_loop()
            try:
                res = await asyncio.wait_for(
                    loop.run_in_executor(None, container.wait),
                    timeout=float(timeout),
                )
                exit_code = res.get("StatusCode", 0)
                stdout_text = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr_text = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                timed_out = True
                exit_code = -1
                logger.warning(f"Container execution timed out after {timeout}s for test {test_case.name}")
                try:
                    container.kill()
                except Exception:
                    pass

        finally:
            # GUARANTEE: Container is destroyed in try/finally
            if container:
                try:
                    container.remove(force=True)
                except Exception as cleanup_err:
                    logger.error(f"Failed to cleanup container {container.id}: {cleanup_err}")

        duration_ms = (time.monotonic() - start_time) * 1000.0
        status, err_msg, stack = self.classify_result(exit_code, stdout_text, stderr_text, timed_out=timed_out)

        return TestResultItem(
            test_case_id=test_case.id,
            test_name=test_case.name,
            status=status,
            duration_ms=round(duration_ms, 2),
            error_message=err_msg,
            stack_trace=stack,
            stdout=stdout_text or None,
            stderr=stderr_text or None,
        )

    async def execute_test_suite(
        self,
        project_id: uuid.UUID,
        test_cases: List[TestCase],
        triggered_by: str = "SYSTEM",
        commit_sha: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> TestExecution:
        """Execute full test suite and persist TestExecution record."""
        now = utc_now()
        execution_id = uuid.uuid4()
        start_time = time.monotonic()

        execution = TestExecution(
            id=execution_id,
            project_id=project_id,
            triggered_by=triggered_by,
            environment=ExecutionEnvironment.DOCKER_SANDBOX,
            commit_sha=commit_sha,
            test_case_ids=[t.id for t in test_cases],
            status=ExecutionStatus.RUNNING,
            total_tests=len(test_cases),
            passed_tests=0,
            failed_tests=0,
            errored_tests=0,
            total_duration_ms=0.0,
            results=[],
            created_at=now,
            updated_at=now,
        )

        # In case Docker is unavailable, raise typed error
        if not self.is_docker_available():
            raise DockerUnavailableError(
                "Docker daemon is not accessible. Cannot start isolated sandbox container execution."
            )

        results: List[TestResultItem] = []
        passed = 0
        failed = 0
        errored = 0

        for tc in test_cases:
            item = await self.run_single_test_container(tc, timeout_seconds=timeout_seconds)
            results.append(item)
            if item.status == ExecutionStatus.PASSED:
                passed += 1
            else:
                if item.status == ExecutionStatus.FAILED:
                    failed += 1
                else:
                    errored += 1

                try:
                    from app.failures.store import FailureStore
                    from shared.schemas.failure import (
                        Failure,
                        FailureCategory,
                        FailureSeverity,
                        FailureStatus,
                        RootCauseAnalysis,
                    )
                    f_store = FailureStore()
                    cat = FailureCategory.ASSERTION_FAILED if item.status == ExecutionStatus.FAILED else (
                        FailureCategory.TIMEOUT if item.status == ExecutionStatus.TIMED_OUT else FailureCategory.LOGIC_ERROR
                    )
                    rca = None
                    if item.error_message:
                        rca = RootCauseAnalysis(
                            summary=f"Automated failure triage for {item.test_name}: {item.error_message[:120]}",
                            file_path=tc.file_path,
                            explanation=f"Execution in isolated Docker sandbox yielded {item.status.value}: {item.error_message}",
                            suggested_fix="Inspect assertion logic and target entity implementation to satisfy test constraints.",
                            confidence_score=0.88,
                        )
                    fail_rec = Failure(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        test_execution_id=execution_id,
                        test_case_id=tc.id,
                        title=f"{item.status.value}: {item.test_name}",
                        error_message=item.error_message or "Test assertion or execution failure encountered.",
                        stack_trace=item.stack_trace,
                        category=cat,
                        severity=FailureSeverity.CRITICAL if item.status == ExecutionStatus.ERROR else FailureSeverity.MAJOR,
                        status=FailureStatus.ROOT_CAUSE_IDENTIFIED if rca else FailureStatus.DETECTED,
                        root_cause=rca,
                        occurrences_count=1,
                    )
                    await f_store.save(fail_rec)
                except Exception as fail_err:
                    logger.warning(f"Failed to record failure defect: {fail_err}")

        total_duration = (time.monotonic() - start_time) * 1000.0

        overall_status = ExecutionStatus.PASSED
        if errored > 0:
            overall_status = ExecutionStatus.ERROR
        elif failed > 0:
            overall_status = ExecutionStatus.FAILED

        execution.status = overall_status
        execution.results = results
        execution.passed_tests = passed
        execution.failed_tests = failed
        execution.errored_tests = errored
        execution.total_duration_ms = round(total_duration, 2)
        execution.updated_at = utc_now()

        # Persist in PostgreSQL
        await self.store.save(execution)
        return execution
