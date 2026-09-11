"""
CodeSentinel Profiler Test Suite: Deep Codebase Intelligence.

Tests framework detection, dependency extraction, AST route parsing, existing tests,
Docker/CI detection, and frozen Project Pydantic model validation.
"""

import os
import tempfile
import pytest

from shared.schemas.project import Project, ProjectStatus
from app.ingestion.file_scanner import FileScanner
from app.profiler.cicd_detector import CicdDetector
from app.profiler.dependency_extractor import DependencyExtractor
from app.profiler.framework_detector import FrameworkDetector
from app.profiler.route_detector import RouteDetector
from app.profiler.service import ProjectProfiler
from app.profiler.test_detector import TestDetector
from tests.fixtures.ingestion.make_fixtures import (
    create_empty_repo,
    create_mixed_repo,
    create_node_express_repo,
    create_python_fastapi_repo,
)


class TestIngestionProfiler:
    """Validates profiling accuracy and schema compliance."""

    def test_python_fastapi_repository_profiling(self):
        """
        REQUIREMENT #1: Small real-shaped Python/FastAPI sample repo ->
        assert correct language, framework, dependencies, and API route detection.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            create_python_fastapi_repo(temp_dir)

            project = ProjectProfiler.profile_directory(
                root_dir=temp_dir,
                project_name="FastAPI-Test-Repo",
                repository_url="https://github.com/org/fastapi-test.git",
            )

            # 1. Validate Project Model Structure
            assert isinstance(project, Project)
            assert project.name == "FastAPI-Test-Repo"
            assert project.status == ProjectStatus.READY
            assert project.total_files >= 4
            assert project.total_lines_of_code > 10

            # 2. Validate Language
            metadata = project.metadata
            assert metadata["primary_language"] == "python"
            assert "python" in metadata["languages"]

            # 3. Validate Framework
            framework_names = [f["name"] for f in metadata["frameworks"]]
            assert "FastAPI" in framework_names

            # 4. Validate Dependencies
            prod_dep_names = [d["name"] for d in metadata["dependencies"]["production"]]
            assert "fastapi" in prod_dep_names
            assert "uvicorn" in prod_dep_names

            # 5. Validate AST API Routes
            routes = metadata["apis"]
            route_paths = [r["path"] for r in routes]
            assert "/health" in route_paths
            assert "/items" in route_paths
            assert "/items/{item_id}" in route_paths

            # Check route details
            health_route = next(r for r in routes if r["path"] == "/health")
            assert health_route["method"] == "GET"
            assert health_route["framework"] == "FastAPI"
            assert health_route["handler_name"] == "health_check"

            # 6. Validate Existing Tests
            tests = metadata["tests"]
            assert tests["has_tests"] is True
            assert "pytest" in tests["test_frameworks"]
            assert any("test_main.py" in f for f in tests["test_files"])

            # 7. Validate Docker and CI
            assert metadata["docker"]["detected"] is True
            assert metadata["ci_cd"]["detected"] is True
            assert "github_actions" in metadata["ci_cd"]["systems"]

            # 8. Validate Tags
            assert "python" in project.tags
            assert "fastapi" in project.tags
            assert "docker" in project.tags
            assert "ci-cd" in project.tags

    def test_node_express_repository_profiling(self):
        """
        REQUIREMENT #2: Small Node/Express sample repo ->
        same assertions for JS/TS path.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            create_node_express_repo(temp_dir)

            project = ProjectProfiler.profile_directory(
                root_dir=temp_dir,
                project_name="Express-Test-Repo",
            )

            assert isinstance(project, Project)
            assert project.name == "Express-Test-Repo"
            metadata = project.metadata

            # Language
            assert metadata["primary_language"] == "javascript"

            # Framework
            framework_names = [f["name"] for f in metadata["frameworks"]]
            assert "Express" in framework_names

            # Dependencies
            prod_dep_names = [d["name"] for d in metadata["dependencies"]["production"]]
            assert "express" in prod_dep_names
            assert "cors" in prod_dep_names

            dev_dep_names = [d["name"] for d in metadata["dependencies"]["development"]]
            assert "jest" in dev_dep_names

            # Routes
            routes = metadata["apis"]
            route_paths = [r["path"] for r in routes]
            assert "/api/users" in route_paths

            # Tests
            assert metadata["tests"]["has_tests"] is True
            assert "jest" in metadata["tests"]["test_frameworks"]

            # Docker
            assert metadata["docker"]["detected"] is True

    def test_mixed_language_repository_profiling(self):
        """
        REQUIREMENT #3: Mixed-language repo (Python backend + JS frontend) ->
        assert both are detected correctly and not confused with each other.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            create_mixed_repo(temp_dir)

            project = ProjectProfiler.profile_directory(
                root_dir=temp_dir,
                project_name="Monorepo-Mixed",
            )

            metadata = project.metadata

            # Both languages detected
            assert "python" in metadata["languages"]
            assert "typescript" in metadata["languages"] or "javascript" in metadata["languages"]

            # Both frameworks detected
            framework_names = [f["name"] for f in metadata["frameworks"]]
            assert "FastAPI" in framework_names
            assert "React" in framework_names

            # Both dependency ecosystems extracted
            prod_deps = [d["name"] for d in metadata["dependencies"]["production"]]
            assert "fastapi" in prod_deps
            assert "react" in prod_deps

            # Docker compose detected
            assert metadata["docker"]["detected"] is True

    def test_empty_no_framework_repository(self):
        """
        REQUIREMENT #4: Repo with no recognizable framework/dependency files ->
        assert it succeeds with empty lists, not an error.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            create_empty_repo(temp_dir)

            project = ProjectProfiler.profile_directory(
                root_dir=temp_dir,
                project_name="Empty-Docs-Repo",
            )

            assert isinstance(project, Project)
            assert project.status == ProjectStatus.READY
            metadata = project.metadata

            # Empty but valid metadata structures
            assert metadata["frameworks"] == []
            assert metadata["dependencies"]["production"] == []
            assert metadata["apis"] == []
            assert metadata["tests"]["has_tests"] is False
            assert metadata["docker"]["detected"] is False
            assert metadata["ci_cd"]["detected"] is False
