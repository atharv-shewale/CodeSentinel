"""
CodeSentinel Sandbox Module: Security & Hardening Configuration.

Enforces:
1. Network isolation: strictly network_mode='none' for test execution stage.
2. Read-only root filesystem with size-limited tmpfs (/tmp size=64m, noexec, nodev, nosuid).
3. Non-root user execution (1000:1000).
4. Strict resource limits: memory (256m), CPU quota (1.0 core), PIDs limit (64).
5. Wall-clock timeout enforcement independent of guest test frameworks.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SandboxSecurityProfile(BaseModel):
    """Immutable security profile applied to all ephemeral test execution containers."""

    # 1. User privileges: Container runs as non-root
    user: str = Field(default="1000:1000", description="Non-root UID:GID")

    # 2. Filesystem hardening: Read-only rootfs + size-bounded tmpfs
    read_only_rootfs: bool = Field(default=True, description="Enforce read-only root filesystem")
    tmpfs_mounts: Dict[str, str] = Field(
        default_factory=lambda: {"/tmp": "size=64m,noexec,nodev,nosuid"},
        description="Scoped ephemeral writable in-memory mounts",
    )

    # 3. Network isolation: Test execution stage MUST be none
    test_network_mode: str = Field(default="none", description="Docker network mode during test execution")
    install_network_mode: Optional[str] = Field(
        default=None,
        description="Optional isolated network for package installation stage before test execution"
    )

    # 4. Resource bounds
    mem_limit: str = Field(default="256m", description="Max container RAM limit")
    memswap_limit: str = Field(default="256m", description="Max RAM + swap limit (prevents swap escapes)")
    nano_cpus: int = Field(default=1_000_000_000, description="Max CPU limit (1.0 core = 1e9 nanoseconds)")
    pids_limit: int = Field(default=64, description="Max process/thread limit to prevent fork bombs")

    # 5. Wall-clock timeout
    default_timeout_seconds: int = Field(default=120, description="Hard timeout before container SIGKILL")

    # 6. Capabilities dropping
    cap_drop: list[str] = Field(
        default_factory=lambda: ["ALL"],
        description="Drop all Linux capabilities for minimal privilege attack surface"
    )

    def to_docker_host_config(self, execution_stage: str = "TEST") -> Dict[str, Any]:
        """
        Build host_config parameters for docker-py container creation.
        Stage 'TEST' strictly enforces network_mode='none'.
        """
        network_mode = self.test_network_mode if execution_stage == "TEST" else (self.install_network_mode or "none")

        return {
            "network_mode": network_mode,
            "read_only": self.read_only_rootfs,
            "tmpfs": self.tmpfs_mounts,
            "mem_limit": self.mem_limit,
            "memswap_limit": self.memswap_limit,
            "nano_cpus": self.nano_cpus,
            "pids_limit": self.pids_limit,
            "cap_drop": self.cap_drop,
        }

    def validate_security_invariants(self) -> None:
        """Assert compliance with CodeSentinel security specifications."""
        assert self.user not in ("root", "0", "0:0", ""), "Security Invariant Violated: Container must not run as root!"
        assert self.test_network_mode == "none", "Security Invariant Violated: Test execution must use network_mode='none'!"
        assert self.read_only_rootfs is True, "Security Invariant Violated: Root filesystem must be read-only!"
        assert "/tmp" in self.tmpfs_mounts, "Security Invariant Violated: Size-limited tmpfs must be mounted at /tmp!"
        assert self.pids_limit <= 128, "Security Invariant Violated: PID limit must be constrained to <= 128!"
