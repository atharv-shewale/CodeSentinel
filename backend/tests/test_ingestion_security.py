"""
CodeSentinel Security Test Suite: Ingestion & Archive Defense.

Validates Zip-Slip defense against path-traversal exploits, quota enforcement,
corrupt archive handling, and Git failure recovery.
"""

import os
import tempfile
import pytest
from app.ingestion.git_service import GitAcquisitionError, GitService
from app.ingestion.zip_service import ZipSecurityError, ZipService
from tests.fixtures.ingestion.make_fixtures import (
    create_malicious_absolute_path_zip,
    create_malicious_zip_slip,
    create_oversized_zip,
)


class TestIngestionSecurity:
    """Verifies sandboxing and defense mechanisms."""

    def test_zip_slip_exploit_rejected(self):
        """
        SECURITY REQUIREMENT #6:
        Attempt a real Zip-Slip exploit with '../evil.sh'. Verify that extraction fails
        with a ZipSecurityError and NO file is written outside the sandboxed extraction root.
        """
        malicious_zip_bytes = create_malicious_zip_slip()

        # Track external canary file path that would be written if exploit succeeded
        temp_parent = tempfile.gettempdir()
        canary_path = os.path.join(temp_parent, "evil.sh")
        if os.path.exists(canary_path):
            os.remove(canary_path)

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(malicious_zip_bytes)

        # Assert error code and message
        assert exc_info.value.code in ("ZIP_PATH_TRAVERSAL_DETECTED", "ZIP_ESCAPE_DETECTED")
        assert "traversal" in exc_info.value.message.lower() or "escapes" in exc_info.value.message.lower()

        # Assert canary file was NEVER created on disk
        assert not os.path.exists(canary_path), "CRITICAL: Zip-Slip exploit succeeded and wrote file outside sandbox!"

    def test_absolute_path_zip_rejected(self):
        """Verify that ZIP archives containing absolute path entries are blocked."""
        malicious_zip_bytes = create_malicious_absolute_path_zip()

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(malicious_zip_bytes)

        assert exc_info.value.code in ("ZIP_ABSOLUTE_PATH_DETECTED", "ZIP_ESCAPE_DETECTED", "ZIP_PATH_TRAVERSAL_DETECTED")

    def test_corrupt_non_zip_file_rejected(self):
        """Verify that corrupt or non-ZIP bytes return a clean typed ZipSecurityError."""
        corrupt_bytes = b"THIS IS NOT A VALID ZIP HEADER"

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(corrupt_bytes)

        assert exc_info.value.code in ("ZIP_CORRUPT_ARCHIVE", "ZIP_OPEN_ERROR")

    def test_zip_file_count_limit_enforced_pre_extraction(self):
        """Verify that archives with excessive file count are rejected before extraction."""
        # Create ZIP with 50 files, set limit to 20
        oversized_zip = create_oversized_zip(file_count=50, file_size_bytes=10)

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(oversized_zip, max_file_count=20)

        assert exc_info.value.code == "ZIP_MAX_FILES_EXCEEDED"

    def test_zip_uncompressed_size_limit_enforced_pre_extraction(self):
        """Verify that archives with excessive total uncompressed size are rejected before extraction."""
        # Create ZIP with 10 files of 1000 bytes (10KB total), set limit to 5KB
        oversized_zip = create_oversized_zip(file_count=10, file_size_bytes=1000)

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(oversized_zip, max_uncompressed_bytes=5000)

        assert exc_info.value.code == "ZIP_MAX_SIZE_EXCEEDED"

    @pytest.mark.asyncio
    async def test_invalid_git_url_raises_typed_error(self):
        """Verify that unreachable or invalid GitHub URLs raise typed GitAcquisitionError."""
        with pytest.raises(GitAcquisitionError) as exc_info:
            await GitService.clone_repository(
                repository_url="https://invalid-domain-that-does-not-exist-12345.com/nonexistent/repo.git",
                timeout_seconds=5,
            )

        assert exc_info.value.code in ("GIT_CLONE_FAILED", "GIT_CLONE_TIMEOUT")

    def test_symlink_escape_exploit_rejected(self):
        """Verify that ZIP archives containing symlinks pointing outside extraction root are rejected."""
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            info = zipfile.ZipInfo("symlink_exploit")
            info.create_system = 3  # Unix
            info.external_attr = 0o120777 << 16  # Symlink mode
            zf.writestr(info, "../../etc/shadow_escape_target")

        symlink_zip_bytes = buf.getvalue()

        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(symlink_zip_bytes)

        assert exc_info.value.code == "ZIP_SYMLINK_ESCAPE_DETECTED"
        assert "symlink" in exc_info.value.message.lower()

    def test_malformed_zip_upload_rejected(self):
        """Verify that truncated, corrupted, or structurally broken ZIP archives raise clean typed errors."""
        # Truncated zip header
        malformed_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00corrupt"
        with pytest.raises(ZipSecurityError) as exc_info:
            ZipService.validate_and_extract_zip(malformed_bytes)

        assert exc_info.value.code in ("ZIP_CORRUPT_ARCHIVE", "ZIP_OPEN_ERROR")

    @pytest.mark.asyncio
    async def test_git_clone_timeout_enforced(self, monkeypatch):
        """Verify that slow git clones exceeding the timeout raise GIT_CLONE_TIMEOUT."""
        import asyncio

        async def mock_wait_for(*args, **kwargs):
            raise asyncio.TimeoutError("Simulated git clone timeout")

        monkeypatch.setattr(asyncio, "wait_for", mock_wait_for)

        with pytest.raises(GitAcquisitionError) as exc_info:
            await GitService.clone_repository(
                repository_url="https://github.com/example/slow-repo.git",
                timeout_seconds=1,
            )

        assert exc_info.value.code == "GIT_CLONE_TIMEOUT"
        assert "timed out" in exc_info.value.message.lower()
