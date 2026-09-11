"""
CodeSentinel Regression Test Suite: Database-Backed ProjectStore.

Simulates separate processes (worker process vs. web process) by instantiating
distinct ProjectStore instances sharing the same database backend, proving that
persisted Project entities are truly relational and cross-process accessible.
"""

from datetime import datetime, timezone
import uuid
import pytest
from shared.schemas.common import utc_now
from shared.schemas.project import Project, ProjectStatus, RepoProvider
from app.core.database import get_sessionmaker
from app.core.project_store import ProjectStore


class TestProjectStorePersistence:
    """Verifies relational persistence and cross-process data round-tripping."""

    @pytest.mark.asyncio
    async def test_cross_process_worker_to_web_simulation(self):
        """
        REGRESSION TEST FOR PERSISTENCE BUG:
        Simulates:
        1. Background Worker process creates ProjectStore instance 'worker_store'.
        2. Worker saves a fully-profiled Project.
        3. Web Server process creates a separate, independent ProjectStore instance 'web_store'.
        4. Web Server retrieves the Project by ID from 'web_store'.
        5. Asserts full equality of all metadata, tags, framework detections, and counts.
        """
        # Create separate store instances pointing at the same database connection pool
        session_maker = get_sessionmaker()
        worker_store = ProjectStore(session_factory=session_maker)
        web_store = ProjectStore(session_factory=session_maker)

        # 1. Worker creates and saves a profiled project
        project_id = uuid.uuid4()
        now = utc_now()
        original_project = Project(
            id=project_id,
            name="Cross-Process-Microservice",
            description="Microservice profiled by background worker process.",
            repository_url="https://github.com/org/microservice.git",
            default_branch="develop",
            provider=RepoProvider.GITHUB,
            tags=["python", "fastapi", "docker", "ci-cd"],
            status=ProjectStatus.READY,
            last_indexed_commit="a1b2c3d4e5f67890",
            total_files=35,
            total_lines_of_code=4820,
            created_at=now,
            updated_at=now,
            metadata={
                "primary_language": "python",
                "languages": {"python": {"files": 30, "loc": 4500, "percentage": 93.3}},
                "frameworks": [
                    {
                        "name": "FastAPI",
                        "category": "backend_web",
                        "confidence_basis": "found in requirements.txt",
                        "version": "0.111.0",
                    }
                ],
                "dependencies": {
                    "production": [{"name": "fastapi", "specifier": ">=0.111.0", "type": "production"}],
                    "development": [{"name": "pytest", "specifier": ">=8.0.0", "type": "development"}],
                },
                "apis": [
                    {
                        "method": "GET",
                        "path": "/api/v1/health",
                        "file_path": "app/main.py",
                        "line_number": 15,
                        "handler_name": "health",
                        "framework": "FastAPI",
                    }
                ],
                "tests": {
                    "has_tests": True,
                    "total_test_files": 3,
                    "test_files": ["tests/test_api.py"],
                    "test_frameworks": ["pytest"],
                },
                "docker": {"detected": True, "files": ["Dockerfile"]},
                "ci_cd": {"detected": True, "systems": ["github_actions"], "files": [".github/workflows/ci.yml"]},
            },
        )

        # Worker writes project
        saved = await worker_store.save_project(original_project)
        assert saved.id == project_id

        # 2. Web process reads project from separate store instance
        retrieved = await web_store.get_project(project_id)
        assert retrieved is not None
        assert retrieved.id == original_project.id
        assert retrieved.name == original_project.name
        assert retrieved.repository_url == original_project.repository_url
        assert retrieved.default_branch == original_project.default_branch
        assert retrieved.provider == original_project.provider
        assert retrieved.status == ProjectStatus.READY
        assert retrieved.last_indexed_commit == "a1b2c3d4e5f67890"
        assert retrieved.total_files == 35
        assert retrieved.total_lines_of_code == 4820
        assert retrieved.tags == ["python", "fastapi", "docker", "ci-cd"]

        # Deep metadata checks
        assert retrieved.metadata["primary_language"] == "python"
        assert retrieved.metadata["frameworks"][0]["name"] == "FastAPI"
        assert retrieved.metadata["apis"][0]["path"] == "/api/v1/health"
        assert retrieved.metadata["docker"]["detected"] is True
        assert retrieved.metadata["ci_cd"]["systems"] == ["github_actions"]

        # 3. Worker updates project status
        original_project.status = ProjectStatus.ACTIVE
        original_project.name = "Cross-Process-Microservice-Renamed"
        await worker_store.save_project(original_project)

        # 4. Web process observes the update immediately
        updated = await web_store.get_project(project_id)
        assert updated is not None
        assert updated.status == ProjectStatus.ACTIVE
        assert updated.name == "Cross-Process-Microservice-Renamed"

        # 5. Web process deletes project; worker process sees it gone
        deleted = await web_store.delete_project(project_id)
        assert deleted is True

        worker_check = await worker_store.get_project(project_id)
        assert worker_check is None

    @pytest.mark.asyncio
    async def test_store_list_all_and_clear(self):
        """Verify list_all and clear across database store instances."""
        session_maker = get_sessionmaker()
        store_a = ProjectStore(session_factory=session_maker)
        store_b = ProjectStore(session_factory=session_maker)

        await store_a.clear_all()

        p1 = Project(
            id=uuid.uuid4(),
            name="Project Alpha",
            repository_url="https://github.com/org/alpha.git",
            status=ProjectStatus.READY,
        )
        p2 = Project(
            id=uuid.uuid4(),
            name="Project Beta",
            repository_url="https://github.com/org/beta.git",
            status=ProjectStatus.READY,
        )

        await store_a.save_project(p1)
        await store_a.save_project(p2)

        listed = await store_b.list_all_projects()
        listed_ids = [p.id for p in listed]
        assert p1.id in listed_ids
        assert p2.id in listed_ids

        await store_b.clear_all()
        listed_after = await store_a.list_all_projects()
        assert len(listed_after) == 0
