"""
CodeSentinel Profiler: Project Profiler Engine.

Coordinates multi-dimensional code intelligence extraction (languages, frameworks,
dependencies, AST API routes, tests, CI/CD) and constructs the strictly-validated
frozen Project Pydantic model.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import uuid
from shared.schemas.common import utc_now
from shared.schemas.project import Project, ProjectStatus, RepoProvider
from app.ingestion.file_scanner import FileScanner, ScanResult
from app.profiler.cicd_detector import CicdDetector
from app.profiler.dependency_extractor import DependencyExtractor
from app.profiler.framework_detector import FrameworkDetector
from app.profiler.route_detector import RouteDetector
from app.profiler.test_detector import TestDetector


class ProjectProfiler:
    """Orchestrates comprehensive profiling of a repository directory into a Project entity."""

    @classmethod
    def profile_directory(
        cls,
        root_dir: str,
        project_id: Optional[uuid.UUID] = None,
        project_name: Optional[str] = None,
        repository_url: str = "",
        default_branch: str = "main",
        provider: RepoProvider = RepoProvider.GITHUB,
        commit_sha: Optional[str] = None,
        scan_result: Optional[ScanResult] = None,
    ) -> Project:
        """
        Run full profiling pipeline on an extracted repository workspace.

        Returns:
            A strictly-validated Project instance (shared.schemas.project.Project).
        """
        pid = project_id or uuid.uuid4()
        name = project_name or os.path.basename(root_dir.rstrip("/\\")) or "unnamed_project"

        # 1. File & Language Scan
        if scan_result is None:
            scan_result = FileScanner.scan_directory(root_dir)

        # 2. Framework Detection
        frameworks = FrameworkDetector.detect(root_dir, scan_result)

        # 3. Dependency Extraction
        dependencies = DependencyExtractor.extract_all(root_dir)

        # 4. AST Route Detection
        routes = RouteDetector.detect_all(root_dir, scan_result)

        # 5. Test Suite Detection
        tests = TestDetector.detect_all(root_dir, scan_result)

        # 6. Docker & CI/CD Pipeline Detection
        cicd = CicdDetector.detect_all(root_dir)

        # 7. Compile Tags
        tags: List[str] = []
        if scan_result.primary_language and scan_result.primary_language != "unknown":
            tags.append(scan_result.primary_language)
        for fw in frameworks:
            tags.append(fw["name"].lower().replace(".", "").replace(" ", "-"))
        if cicd["docker"]["detected"]:
            tags.append("docker")
        if cicd["ci_cd"]["detected"]:
            tags.append("ci-cd")
        if tests["has_tests"]:
            tags.append("has-tests")

        # Deduplicate and sort tags
        unique_tags = sorted(list(set(tags)))

        # 8. Compile Comprehensive Metadata
        metadata: Dict[str, Any] = {
            "primary_language": scan_result.primary_language,
            "languages": scan_result.language_breakdown,
            "frameworks": frameworks,
            "dependencies": dependencies,
            "apis": routes,
            "tests": tests,
            "docker": cicd["docker"],
            "ci_cd": cicd["ci_cd"],
            "root_dir": root_dir,
            "profiled_at": utc_now().isoformat(),
        }

        # 9. Construct and Strictly Validate Project Pydantic Model
        now = utc_now()
        project = Project(
            id=pid,
            name=name[:128],
            description=f"Auto-profiled {scan_result.primary_language} repository ({scan_result.total_files} files, {scan_result.total_lines_of_code} LOC).",
            repository_url=repository_url or f"local://{name}",
            default_branch=default_branch,
            provider=provider,
            tags=unique_tags,
            status=ProjectStatus.READY,
            last_indexed_commit=commit_sha,
            total_files=scan_result.total_files,
            total_lines_of_code=scan_result.total_lines_of_code,
            created_at=now,
            updated_at=now,
            metadata=metadata,
        )

        return project
