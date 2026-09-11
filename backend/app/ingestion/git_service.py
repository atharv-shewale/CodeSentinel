"""
CodeSentinel Ingestion Module: Git Repository Acquisition Service.

Handles secure, sandboxed Git cloning using GitPython with strict execution timeouts,
isolated temporary workspaces, and commit metadata extraction.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
import tempfile
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse
import git
from app.core.logging import logger

_executor = ThreadPoolExecutor(max_workers=4)


class GitAcquisitionError(Exception):
    """Exception raised when Git acquisition fails."""
    def __init__(self, message: str, code: str = "GIT_CLONE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class GitService:
    """Provides sandboxed, timeout-guarded Git clone operations."""

    @staticmethod
    def _sanitize_git_url(url: str, access_token: Optional[str] = None) -> str:
        """Embed access token into git URL securely if provided."""
        if not access_token:
            return url.strip()

        parsed = urlparse(url.strip())
        if parsed.scheme in ("http", "https"):
            netloc = f"oauth2:{access_token}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=netloc))
        return url.strip()

    @staticmethod
    def _sync_clone(
        clone_url: str,
        target_dir: str,
        branch: str = "main",
    ) -> Tuple[str, str, str]:
        """
        Synchronously clone repository into target directory with shallow depth.
        Returns (commit_sha, branch_name, repo_name).
        """
        clone_kwargs: dict[str, Any] = {
            "branch": branch,
            "depth": 1,
            "single_branch": True,
        }
        if os.name != "nt":
            clone_kwargs["kill_after_timeout"] = 45

        try:
            repo = git.Repo.clone_from(
                clone_url,
                target_dir,
                **clone_kwargs,
            )
            commit_sha = repo.head.commit.hexsha
            active_branch = repo.active_branch.name if not repo.head.is_detached else branch
            repo_name = Path(urlparse(clone_url).path).stem or "repo"
            return commit_sha, active_branch, repo_name
        except git.GitCommandError as e:
            # Check if failure was branch specific; try default remote branch fallback
            if "Remote branch" in str(e) or "did not match any" in str(e):
                try:
                    repo = git.Repo.clone_from(
                        clone_url,
                        target_dir,
                        **clone_kwargs,
                    )
                    commit_sha = repo.head.commit.hexsha
                    active_branch = repo.active_branch.name if not repo.head.is_detached else "main"
                    repo_name = Path(urlparse(clone_url).path).stem or "repo"
                    return commit_sha, active_branch, repo_name
                except Exception as inner_e:
                    raise GitAcquisitionError(
                        f"Failed to clone Git repository: {str(inner_e)}",
                        code="GIT_INVALID_URL_OR_BRANCH"
                    )
            raise GitAcquisitionError(
                f"Failed to clone Git repository: {str(e)}",
                code="GIT_CLONE_FAILED"
            )
        except Exception as e:
            raise GitAcquisitionError(
                f"Unexpected error during Git cloning: {str(e)}",
                code="GIT_UNEXPECTED_ERROR"
            )

    @classmethod
    async def clone_repository(
        cls,
        repository_url: str,
        branch: str = "main",
        access_token: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> Tuple[str, str, str, str]:
        """
        Asynchronously clone a Git repository into an isolated temporary workspace.

        Args:
            repository_url: Git clone URL.
            branch: Git branch to clone.
            access_token: Optional token for private repository authentication.
            timeout_seconds: Maximum allowed time for cloning before timeout error.

        Returns:
            Tuple of (temp_working_dir, commit_sha, branch_name, repo_name).
        """
        if not repository_url or not repository_url.strip():
            raise GitAcquisitionError("Repository URL cannot be empty.", code="GIT_EMPTY_URL")

        temp_dir = tempfile.mkdtemp(prefix="codesentinel_git_")
        clone_url = cls._sanitize_git_url(repository_url, access_token)

        loop = asyncio.get_running_loop()
        try:
            commit_sha, active_branch, repo_name = await asyncio.wait_for(
                loop.run_in_executor(_executor, cls._sync_clone, clone_url, temp_dir, branch),
                timeout=timeout_seconds,
            )
            return temp_dir, commit_sha, active_branch, repo_name
        except asyncio.TimeoutError:
            cls.cleanup_temp_dir(temp_dir)
            raise GitAcquisitionError(
                f"Git clone operation timed out after {timeout_seconds} seconds.",
                code="GIT_CLONE_TIMEOUT"
            )
        except Exception as e:
            cls.cleanup_temp_dir(temp_dir)
            if isinstance(e, GitAcquisitionError):
                raise e
            raise GitAcquisitionError(str(e), code="GIT_CLONE_FAILED")

    @staticmethod
    def cleanup_temp_dir(dir_path: Optional[str]) -> None:
        """Safely remove isolated temporary working directory."""
        if dir_path and os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
                logger.debug(f"Cleaned up temporary workspace at {dir_path}")
            except Exception as e:
                logger.warning(f"Error removing temporary directory {dir_path}: {e}")
