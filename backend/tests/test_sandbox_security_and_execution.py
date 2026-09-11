"""
CodeSentinel Module 4 Tests: Sandbox Security & Execution Classification (Tests 8-16).

Verifies:
8. Network isolation: test execution stage uses network_mode='none'.
9. Timeout enforcement: wall-clock timeout kills hanging container and marks TIMED_OUT.
10. Cleanup on crash: container is removed in try/finally even if test crashes or fails.
11. Sandbox-to-app-network isolation: sandbox network remains isolated from app/db network.
12. Resource limits: mem_limit='256m', pids_limit=64, nano_cpus=1e9, read_only=True, tmpfs 64m.
13. Result classification PASS: exit code 0 -> PASSED.
14. Result classification FAIL: AssertionError -> FAILED.
15. Result classification ERROR: missing dependency / ImportError -> ERROR.
16. Result classification TIMEOUT: execution timeout -> TIMED_OUT.
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch

from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from shared.schemas.test_execution import ExecutionStatus, TestExecution
from app.sandbox.executor import DockerSandboxExecutor, DockerUnavailableError
from app.sandbox.security import SandboxSecurityProfile

# Prevent pytest from attempting to collect imported schema classes as test suites
TestCase.__test__ = False
TestProvenance.__test__ = False
TestStatus.__test__ = False
TestType.__test__ = False
TestExecution.__test__ = False


def test_sandbox_security_profile_invariants():
    """Test 8 & 12: Validates network isolation, read-only rootfs, non-root user, and resource limits."""
    profile = SandboxSecurityProfile()
    profile.validate_security_invariants()

    host_config = profile.to_docker_host_config(execution_stage="TEST")

    # Invariant: Non-root user
    assert profile.user not in ("root", "0", "0:0", "")
    assert profile.user == "1000:1000"

    # Invariant: Network isolation
    assert host_config["network_mode"] == "none", "Test execution stage MUST have network_mode='none'!"

    # Invariant: Read-only root filesystem
    assert host_config["read_only"] is True, "Root filesystem MUST be read-only!"

    # Invariant: Ephemeral size-limited tmpfs
    assert "/tmp" in host_config["tmpfs"]
    assert "size=64m" in host_config["tmpfs"]["/tmp"]
    assert "noexec" in host_config["tmpfs"]["/tmp"]

    # Invariant: Resource limits
    assert host_config["mem_limit"] == "256m"
    assert host_config["memswap_limit"] == "256m"
    assert host_config["nano_cpus"] == 1_000_000_000  # 1.0 CPU
    assert host_config["pids_limit"] == 64


def test_sandbox_app_network_isolation():
    """Test 11: Sandbox-to-app-network isolation."""
    profile = SandboxSecurityProfile()
    test_config = profile.to_docker_host_config(execution_stage="TEST")

    # App networks (e.g. codesentinel_app_net, host, bridge) MUST NOT be attached
    forbidden_networks = ["host", "bridge", "codesentinel_app_net", "default"]
    assert test_config["network_mode"] not in forbidden_networks
    assert test_config["network_mode"] == "none"


@pytest.mark.asyncio
async def test_container_cleanup_on_crash():
    """Test 10: Cleanup on crash - container.remove(force=True) is guaranteed in finally block."""
    executor = DockerSandboxExecutor()

    mock_container = MagicMock()
    mock_container.wait.side_effect = RuntimeError("Simulated catastrophic container crash!")

    mock_docker_client = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container
    mock_docker_client.ping.return_value = True

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="test_crashing_suite",
        description="Verify container cleanup on crash",
        test_type=TestType.UNIT,
        provenance=TestProvenance.COVERAGE_ONLY,
        file_path="tests/test_crash.py",
        test_code="def test_crashing_suite(): pass",
        status=TestStatus.ACTIVE,
    )

    with patch.object(executor, "_get_docker_client", return_value=mock_docker_client):
        try:
            await executor.run_single_test_container(tc, timeout_seconds=5)
        except Exception:
            pass

        # Verify container.remove(force=True) was explicitly invoked despite the crash
        mock_container.remove.assert_called_once_with(force=True)


@pytest.mark.asyncio
async def test_timeout_enforcement_kills_container():
    """Test 9: Timeout enforcement - wall-clock timeout kills hanging container and classifies TIMED_OUT."""
    executor = DockerSandboxExecutor()

    mock_container = MagicMock()
    # Simulate wait hanging forever
    import time
    def slow_wait():
        time.sleep(10)
        return {"StatusCode": 0}

    mock_container.wait.side_effect = slow_wait
    mock_container.logs.return_value = b""

    mock_docker_client = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container
    mock_docker_client.ping.return_value = True

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="test_infinite_loop",
        description="Verify container timeout enforcement and kill",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/test_loop.py",
        test_code="def test_infinite_loop(): while True: pass",
        status=TestStatus.ACTIVE,
    )

    with patch.object(executor, "_get_docker_client", return_value=mock_docker_client):
        # Timeout set to 0.1s for fast test execution
        result = await executor.run_single_test_container(tc, timeout_seconds=1)

        assert result.status == ExecutionStatus.TIMED_OUT
        # Verify container kill and removal were executed
        mock_container.kill.assert_called_once()
        mock_container.remove.assert_called_once_with(force=True)


def test_classification_pass():
    """Test 13: Clean pass exit 0 classified as PASSED."""
    status, err_msg, stack = DockerSandboxExecutor.classify_result(
        exit_code=0,
        stdout="1 passed in 0.05s",
        stderr="",
        timed_out=False,
    )
    assert status == ExecutionStatus.PASSED
    assert err_msg is None


def test_classification_fail():
    """Test 14: Assertion failure exit 1 classified as FAILED."""
    status, err_msg, stack = DockerSandboxExecutor.classify_result(
        exit_code=1,
        stdout="",
        stderr="AssertionError: assert 401 == 200\n  +401\n  -200",
        timed_out=False,
    )
    assert status == ExecutionStatus.FAILED
    assert "AssertionError" in (err_msg or "")


def test_classification_error_missing_dependency():
    """Test 15: Missing dependency / import error classified as ERROR."""
    status, err_msg, stack = DockerSandboxExecutor.classify_result(
        exit_code=2,
        stdout="",
        stderr="ModuleNotFoundError: No module named 'cryptography'",
        timed_out=False,
    )
    assert status == ExecutionStatus.ERROR
    assert "ModuleNotFoundError" in (err_msg or "")


def test_classification_timeout():
    """Test 16: Wall-clock timeout classified as TIMED_OUT."""
    status, err_msg, stack = DockerSandboxExecutor.classify_result(
        exit_code=-1,
        stdout="",
        stderr="",
        timed_out=True,
    )
    assert status == ExecutionStatus.TIMED_OUT
    assert "timeout" in (err_msg or "").lower()


# ==============================================================================
# Behavioral Live Container Exploit Tests (Phase 4 Security Enforcement)
# ==============================================================================

@pytest.mark.asyncio
async def test_network_isolation_blocks_outbound_call():
    """1. Behavioral exploit: outbound HTTP call from inside sandbox container must fail."""
    executor = DockerSandboxExecutor()
    if not executor.is_docker_available():
        pytest.skip("Docker daemon unavailable for live container test")

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="exploit_outbound_http",
        description="Exploit attempt: outbound HTTP exfiltration",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/exploit_outbound.py",
        test_code="""
def exploit_outbound_http():
    import urllib.request
    # Attempt outbound HTTP connection to public IP
    urllib.request.urlopen("http://1.1.1.1", timeout=2)
""",
        status=TestStatus.ACTIVE,
    )

    result = await executor.run_single_test_container(tc, timeout_seconds=5)

    # Call MUST NOT succeed
    assert result.status != ExecutionStatus.PASSED, "Security failure: outbound call succeeded!"
    combined = f"{result.stderr or ''} {result.error_message or ''}"
    assert any(msg in combined for msg in ["Network is unreachable", "URLError", "timeout", "Errno 101"]), (
        f"Expected network unreachable error, got: {combined}"
    )


@pytest.mark.asyncio
async def test_sandbox_cannot_reach_app_services():
    """2. Behavioral exploit: connections to Postgres, Neo4j, Qdrant, Redis must all fail."""
    from app.core.config import settings

    executor = DockerSandboxExecutor()
    if not executor.is_docker_available():
        pytest.skip("Docker daemon unavailable for live container test")

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="exploit_reach_app_services",
        description="Exploit attempt: connect to Postgres, Neo4j, Qdrant, Redis",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/exploit_services.py",
        test_code=f"""
def exploit_reach_app_services():
    import socket
    services = [
        ("postgres", "{settings.POSTGRES_SERVER}", {settings.POSTGRES_PORT}),
        ("neo4j", "localhost", 7687),
        ("qdrant", "{settings.QDRANT_HOST}", {settings.QDRANT_PORT}),
        ("redis", "{settings.REDIS_HOST}", {settings.REDIS_PORT}),
        ("host_gateway", "host.docker.internal", 5432),
    ]
    connected = []
    for name, host, port in services:
        try:
            s = socket.create_connection((host, port), timeout=1.0)
            s.close()
            connected.append(f"{{name}}({{host}}:{{port}})")
        except Exception:
            pass  # Expected: blocked by network_mode='none'
            
    assert len(connected) == 0, f"SECURITY BREACH: Reached internal services: {{connected}}"
""",
        status=TestStatus.ACTIVE,
    )

    result = await executor.run_single_test_container(tc, timeout_seconds=10)

    # If any service was reached, the container assertion fails with SECURITY BREACH
    assert result.status == ExecutionStatus.PASSED, f"Exploit connected to app services: {result.stderr or result.error_message}"


@pytest.mark.asyncio
async def test_readonly_filesystem_blocks_writes_outside_tmp():
    """3. Behavioral exploit: write outside permitted tmpfs path (/app or /) must fail."""
    executor = DockerSandboxExecutor()
    if not executor.is_docker_available():
        pytest.skip("Docker daemon unavailable for live container test")

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="exploit_write_rootfs",
        description="Exploit attempt: write to read-only rootfs",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/exploit_fs.py",
        test_code="""
def exploit_write_rootfs():
    # Attempt to write outside /tmp (e.g. to / or /app)
    with open("/malicious_payload.sh", "w") as f:
        f.write("#!/bin/sh\\necho pwned")
""",
        status=TestStatus.ACTIVE,
    )

    result = await executor.run_single_test_container(tc, timeout_seconds=5)

    # Must fail and trigger Read-only file system error
    assert result.status != ExecutionStatus.PASSED, "Security failure: write to rootfs succeeded!"
    combined = f"{result.stderr or ''} {result.error_message or ''}"
    assert "Read-only file system" in combined or "Errno 30" in combined, (
        f"Expected Read-only file system error, got: {combined}"
    )


@pytest.mark.asyncio
async def test_memory_limit_kills_overallocation():
    """4. Behavioral exploit: deliberate overallocation (512MB vs 256MB) kills container/OOMs."""
    executor = DockerSandboxExecutor()
    if not executor.is_docker_available():
        pytest.skip("Docker daemon unavailable for live container test")

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="exploit_memory_exhaustion",
        description="Exploit attempt: allocate 512MB beyond 256MB limit",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/exploit_mem.py",
        test_code="""
def exploit_memory_exhaustion():
    # Attempt to allocate 512MB in 1MB chunks
    chunks = []
    for _ in range(512):
        chunks.append(b"X" * (1024 * 1024))
""",
        status=TestStatus.ACTIVE,
    )

    result = await executor.run_single_test_container(tc, timeout_seconds=10)

    # Container must be killed / OOM'd rather than silently succeeding
    assert result.status != ExecutionStatus.PASSED, "Security failure: memory overallocation silently succeeded!"
    combined = f"{result.stderr or ''} {result.error_message or ''}"
    assert (
        result.status in (ExecutionStatus.ERROR, ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT)
        and any(indicator in combined for indicator in ["137", "OOM", "Out of Memory", "MemoryError", "SIGKILL"])
    ), f"Expected container to be killed by OOM (exit code 137/MemoryError), got: status={result.status}, msg={combined}"


@pytest.mark.asyncio
async def test_pids_limit_blocks_fork_bomb():
    """5. Behavioral exploit: spawning processes beyond pids_limit=64 is blocked/killed."""
    executor = DockerSandboxExecutor()
    if not executor.is_docker_available():
        pytest.skip("Docker daemon unavailable for live container test")

    tc = TestCase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="exploit_fork_bomb",
        description="Exploit attempt: fork bomb exceeding 64 PIDs",
        test_type=TestType.UNIT,
        provenance=TestProvenance.AI_INFERRED,
        file_path="tests/exploit_pids.py",
        test_code="""
def exploit_fork_bomb():
    import os, time
    children = []
    try:
        # Attempt to spawn 120 processes (well above 64 limit)
        for _ in range(120):
            pid = os.fork()
            if pid == 0:
                time.sleep(5)
                os._exit(0)
            children.append(pid)
    finally:
        for c in children:
            try:
                os.kill(c, 9)
            except Exception:
                pass
""",
        status=TestStatus.ACTIVE,
    )

    result = await executor.run_single_test_container(tc, timeout_seconds=10)

    # Must be blocked/killed rather than silently spawning all 120 processes
    assert result.status != ExecutionStatus.PASSED, "Security failure: fork bomb spawned beyond limit!"
    combined = f"{result.stderr or ''} {result.error_message or ''}"
    assert any(indicator in combined for indicator in ["BlockingIOError", "Errno 11", "Resource temporarily unavailable", "137", "killed"]), (
        f"Expected fork bomb to be blocked by cgroups pids_limit (Errno 11 / BlockingIOError), got: {combined}"
    )

