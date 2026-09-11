"""
CodeSentinel Ingestion Module: Safe ZIP Archive Extraction Service.

Enforces strict Zip-Slip defenses, symlink target containment, pre-extraction
size & file count quotas, and isolated temp workspace extraction.
"""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path
import shutil
import tempfile
from typing import Optional, Tuple
import zipfile
from app.core.logging import logger

DEFAULT_MAX_ZIP_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_MAX_ZIP_FILE_COUNT = 10000


class ZipSecurityError(Exception):
    """Exception raised for security violations or invalid zip archives."""
    def __init__(self, message: str, code: str = "ZIP_SECURITY_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ZipService:
    """Provides sandboxed extraction for ZIP archives with full Zip-Slip defenses."""

    @staticmethod
    def _is_safe_path(base_dir: str, path: str) -> bool:
        """
        Verify that path resolves strictly within base_dir.
        Defends against directory traversal (Zip-Slip), absolute path escapes, and .. sequences.
        """
        base_dir_resolved = os.path.realpath(os.path.abspath(base_dir))
        target_path_resolved = os.path.realpath(os.path.abspath(os.path.join(base_dir, path)))
        return os.path.commonpath([base_dir_resolved, target_path_resolved]) == base_dir_resolved

    @classmethod
    def validate_and_extract_zip(
        cls,
        zip_source: str | bytes | io.BytesIO,
        max_uncompressed_bytes: int = DEFAULT_MAX_ZIP_UNCOMPRESSED_BYTES,
        max_file_count: int = DEFAULT_MAX_ZIP_FILE_COUNT,
    ) -> Tuple[str, str]:
        """
        Safely inspect and extract a ZIP archive into an isolated temporary workspace.

        Args:
            zip_source: File path, raw bytes, or BytesIO stream of the ZIP archive.
            max_uncompressed_bytes: Maximum allowed total uncompressed size.
            max_file_count: Maximum allowed number of files in the archive.

        Returns:
            Tuple of (temp_working_dir, repo_name).

        Raises:
            ZipSecurityError: If archive is corrupt, malicious, or exceeds limits.
        """
        temp_dir = tempfile.mkdtemp(prefix="codesentinel_zip_")

        try:
            if isinstance(zip_source, str) and os.path.isfile(zip_source):
                zip_file = zipfile.ZipFile(zip_source, "r")
                repo_name = Path(zip_source).stem or "uploaded_project"
            elif isinstance(zip_source, bytes):
                zip_file = zipfile.ZipFile(io.BytesIO(zip_source), "r")
                repo_name = "uploaded_project"
            elif isinstance(zip_source, io.BytesIO):
                zip_file = zipfile.ZipFile(zip_source, "r")
                repo_name = "uploaded_project"
            elif isinstance(zip_source, str):
                # Try decoding base64 if passed as string
                try:
                    decoded = base64.b64decode(zip_source)
                    zip_file = zipfile.ZipFile(io.BytesIO(decoded), "r")
                    repo_name = "uploaded_project"
                except Exception:
                    raise ZipSecurityError("Invalid ZIP file path or base64 payload.", code="ZIP_INVALID_SOURCE")
            else:
                raise ZipSecurityError("Unsupported ZIP source format.", code="ZIP_UNSUPPORTED_FORMAT")
        except zipfile.BadZipFile:
            cls.cleanup_temp_dir(temp_dir)
            raise ZipSecurityError("The provided file is not a valid or readable ZIP archive.", code="ZIP_CORRUPT_ARCHIVE")
        except Exception as e:
            cls.cleanup_temp_dir(temp_dir)
            if isinstance(e, ZipSecurityError):
                raise e
            raise ZipSecurityError(f"Error opening ZIP archive: {str(e)}", code="ZIP_OPEN_ERROR")

        # Step 1: Pre-extraction quota check on Central Directory header listing
        with zip_file:
            infolist = zip_file.infolist()
            total_files = len(infolist)
            if total_files > max_file_count:
                cls.cleanup_temp_dir(temp_dir)
                raise ZipSecurityError(
                    f"ZIP archive contains {total_files} files, exceeding limit of {max_file_count}.",
                    code="ZIP_MAX_FILES_EXCEEDED"
                )

            total_uncompressed_bytes = sum(info.file_size for info in infolist)
            if total_uncompressed_bytes > max_uncompressed_bytes:
                cls.cleanup_temp_dir(temp_dir)
                raise ZipSecurityError(
                    f"ZIP archive uncompressed size ({total_uncompressed_bytes} bytes) exceeds maximum allowed ({max_uncompressed_bytes} bytes).",
                    code="ZIP_MAX_SIZE_EXCEEDED"
                )

            # Step 2: Path traversal validation before extracting any file
            for member in infolist:
                filename = member.filename
                # Check for relative path escapes in filename
                if ".." in filename.replace("\\", "/").split("/"):
                    cls.cleanup_temp_dir(temp_dir)
                    raise ZipSecurityError(
                        f"Malicious Zip-Slip traversal sequence detected in member: '{filename}'",
                        code="ZIP_PATH_TRAVERSAL_DETECTED"
                    )

                if os.path.isabs(filename) or filename.startswith(("/", "\\")):
                    cls.cleanup_temp_dir(temp_dir)
                    raise ZipSecurityError(
                        f"Absolute path escape attempt detected in member: '{filename}'",
                        code="ZIP_ABSOLUTE_PATH_DETECTED"
                    )

                if not cls._is_safe_path(temp_dir, filename):
                    cls.cleanup_temp_dir(temp_dir)
                    raise ZipSecurityError(
                        f"Path escapes sandboxed extraction root: '{filename}'",
                        code="ZIP_ESCAPE_DETECTED"
                    )

            # Step 3: Safe Extraction member-by-member
            for member in infolist:
                target_path = os.path.join(temp_dir, member.filename)
                
                # Check if member is a symlink (Unix attribute 0o120000)
                is_symlink = (member.external_attr >> 16) & 0o120000 == 0o120000
                if is_symlink:
                    # Read symlink target from file content without creating unverified link
                    link_target_bytes = zip_file.read(member)
                    link_target = link_target_bytes.decode("utf-8", errors="ignore").strip()
                    target_parent = os.path.dirname(target_path)
                    os.makedirs(target_parent, exist_ok=True)
                    
                    # Verify resolved symlink target stays strictly inside temp_dir
                    resolved_symlink_dest = os.path.realpath(os.path.abspath(os.path.join(target_parent, link_target)))
                    if not cls._is_safe_path(temp_dir, resolved_symlink_dest):
                        cls.cleanup_temp_dir(temp_dir)
                        raise ZipSecurityError(
                            f"Symlink '{member.filename}' -> '{link_target}' points outside extraction directory.",
                            code="ZIP_SYMLINK_ESCAPE_DETECTED"
                        )
                    # Create safe relative symlink or copy
                    try:
                        if hasattr(os, "symlink"):
                            os.symlink(link_target, target_path)
                    except Exception as sym_err:
                        logger.debug(f"Symlink creation skipped on host OS: {sym_err}")
                else:
                    zip_file.extract(member, temp_dir)

        # If the ZIP contained a single top-level directory wrapper, detect and adjust root
        entries = [e for e in os.listdir(temp_dir) if not e.startswith(".")]
        if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
            extracted_root = os.path.join(temp_dir, entries[0])
            repo_name = entries[0]
            return extracted_root, repo_name

        return temp_dir, repo_name

    @staticmethod
    def cleanup_temp_dir(dir_path: Optional[str]) -> None:
        """Safely remove isolated temporary working directory."""
        if dir_path and os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error removing temp directory {dir_path}: {e}")
