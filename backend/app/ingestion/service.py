"""
CodeSentinel Ingestion Module: Ingestion Service Orchestrator.

Manages the end-to-end asynchronous workflow of repository acquisition,
sandboxed extraction, file scanning, deep profiling, and job telemetry.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Optional
import uuid

from shared.schemas.jobs import JobState, JobStatus, JobType
from shared.schemas.project import Project, ProjectStatus, RepoProvider
from app.core.logging import logger
from app.core.project_store import ProjectStore
from app.ingestion.file_scanner import FileScanner
from app.ingestion.git_service import GitAcquisitionError, GitService
from app.ingestion.schemas import IngestRepoRequest, IngestionSourceType
from app.ingestion.zip_service import ZipSecurityError, ZipService
from app.profiler.service import ProjectProfiler
from app.workers.job_manager import JobManager


class IngestionService:
    """Orchestrates asynchronous repository ingestion and profiling jobs."""

    @classmethod
    async def start_ingestion_job(
        cls,
        request: IngestRepoRequest,
        job_id: Optional[str] = None,
    ) -> JobStatus:
        """
        Create background job and launch asynchronous ingestion pipeline.
        """
        source_type = request.get_effective_source_type()
        source_desc = request.get_effective_url_or_source()

        job = await JobManager.create_job(
            job_type=JobType.REPO_INGESTION,
            job_id=job_id,
            total_steps=100,
            initial_message=f"Queued ingestion for {source_type.value} repository ({source_desc})...",
        )

        # Spawn non-blocking background task
        asyncio.create_task(cls._run_ingestion_pipeline(job.job_id, request))
        return job

    @classmethod
    async def _run_ingestion_pipeline(
        cls,
        job_id: str,
        request: IngestRepoRequest,
    ) -> None:
        """
        Background task executing acquisition, scanning, profiling, and cleanup.
        """
        temp_dir: Optional[str] = None
        source_type = request.get_effective_source_type()
        project_id = uuid.uuid4()

        try:
            # Step 1: Acquisition (Git Clone or ZIP Extraction)
            await JobManager.update_progress(
                job_id,
                current_step=15,
                status_message=f"Acquiring repository from {source_type.value} source...",
            )

            commit_sha: Optional[str] = None
            branch_name: str = request.branch or "main"
            repo_name: str = request.project_name or "project"
            provider: RepoProvider = RepoProvider.GITHUB

            if source_type == IngestionSourceType.GITHUB:
                clone_url = request.get_effective_url_or_source()
                if not clone_url:
                    raise GitAcquisitionError("GitHub source URL is required.", code="MISSING_SOURCE_URL")

                temp_dir, commit_sha, branch_name, extracted_name = await GitService.clone_repository(
                    repository_url=clone_url,
                    branch=branch_name,
                    access_token=request.access_token,
                )
                if not request.project_name:
                    repo_name = extracted_name
                provider = RepoProvider.GITHUB

            elif source_type == IngestionSourceType.ZIP:
                zip_source: str | bytes
                if request.zip_base64:
                    zip_source = request.zip_base64
                elif request.file_id:
                    # Check if file_id corresponds to a local temp file
                    candidate_path = os.path.join(tempfile.gettempdir(), f"{request.file_id}.zip")
                    if os.path.isfile(candidate_path):
                        zip_source = candidate_path
                    elif os.path.isfile(request.file_id):
                        zip_source = request.file_id
                    else:
                        raise ZipSecurityError(f"Uploaded ZIP reference '{request.file_id}' not found.", code="ZIP_NOT_FOUND")
                else:
                    raise ZipSecurityError("No ZIP payload or file_id provided.", code="ZIP_PAYLOAD_MISSING")

                temp_dir, extracted_name = ZipService.validate_and_extract_zip(zip_source)
                if not request.project_name:
                    repo_name = extracted_name
                provider = RepoProvider.LOCAL

            else:
                raise ValueError(f"Unsupported source type '{source_type}'.")

            # Step 2: File Tree Scanning & Language Distribution
            await JobManager.update_progress(
                job_id,
                current_step=40,
                status_message="Scanning file tree, respecting .gitignore, and classifying languages...",
            )

            scan_result = FileScanner.scan_directory(temp_dir)

            # Step 3: Deep Profiling (Frameworks, Dependencies, AST Routes, Tests, CI)
            await JobManager.update_progress(
                job_id,
                current_step=70,
                status_message="Detecting frameworks, dependencies, AST routes, and existing test suites...",
            )

            project = ProjectProfiler.profile_directory(
                root_dir=temp_dir,
                project_id=project_id,
                project_name=repo_name,
                repository_url=request.get_effective_url_or_source() or f"local://{repo_name}",
                default_branch=branch_name,
                provider=provider,
                commit_sha=commit_sha,
                scan_result=scan_result,
            )

            # Step 4: Persist in PostgreSQL-backed ProjectStore
            await ProjectStore.save(project)

            # Step 5: Mark Job Complete
            await JobManager.complete_job(
                job_id,
                result=project.model_dump(mode="json"),
                message=f"Successfully profiled project '{project.name}' ({project.total_files} files, {project.total_lines_of_code} LOC).",
            )
            logger.info(f"Ingestion job {job_id} completed successfully for project {project.id}. Retaining source workspace at {temp_dir}.")

        except (GitAcquisitionError, ZipSecurityError) as e:
            logger.error(f"Ingestion job {job_id} failed with domain error: {e}")
            await JobManager.fail_job(job_id, f"{e.code}: {e.message}")
            if temp_dir:
                GitService.cleanup_temp_dir(temp_dir)
        except Exception as e:
            logger.exception(f"Unexpected error in ingestion job {job_id}: {e}")
            await JobManager.fail_job(job_id, f"INGESTION_ERROR: {str(e)}")
            if temp_dir:
                GitService.cleanup_temp_dir(temp_dir)
