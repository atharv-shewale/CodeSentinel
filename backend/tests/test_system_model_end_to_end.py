"""
CodeSentinel End-to-End System Model & Integration Test Suite.

Verifies full assembly of SoftwareSystemModel via GET /api/v1/analysis/{project_id}/system-model,
background analysis jobs, and requirement API endpoints.
"""

import os
import tempfile
import uuid
from fastapi.testclient import TestClient
import pytest
from shared.schemas.project import Project, ProjectStatus, RepoProvider
from app.analyzer.service import CodeAnalyzerService
from app.analyzer.system_model import SoftwareSystemModel
from app.core.project_store import ProjectStore
from app.requirements.service import RequirementService
from tests.fixtures.analysis.sample_sources import SAMPLE_PYTHON_SOURCE
from tests.fixtures.requirements.sample_documents import STRUCTURED_SRS_MARKDOWN


class TestSystemModelEndToEnd:
    """Verifies end-to-end System Model assembly and REST API endpoints."""

    @pytest.mark.asyncio
    async def test_full_system_model_assembly_endpoint(self, client: TestClient):
        """
        TEST #12: End-to-end: given one fixture project with known files, requirements,
        and mappings -> assert GET /api/v1/analysis/{project_id}/system-model returns
        the fully assembled, correctly cross-referenced Software System Model.
        """
        project_id = uuid.uuid4()

        # 1. Register Project in PostgreSQL
        project = Project(
            id=project_id,
            name="Sentinel-Core-Project",
            repository_url="https://github.com/org/sentinel-core.git",
            status=ProjectStatus.READY,
            metadata={
                "primary_language": "python",
                "apis": [{"method": "POST", "path": "/api/v1/auth/login", "framework": "FastAPI"}],
                "dependencies": {"production": [{"name": "fastapi", "type": "production"}]},
            },
        )
        await ProjectStore.save(project)

        # 2. Ingest SRS requirements
        await RequirementService.process_raw_text(
            project_id=project_id,
            text=STRUCTURED_SRS_MARKDOWN,
            source_name="srs.md",
        )

        # 3. Create sample repository tree in temp dir and analyze
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, "app")
            os.makedirs(app_dir, exist_ok=True)
            with open(os.path.join(app_dir, "auth.py"), "w", encoding="utf-8") as f:
                f.write(SAMPLE_PYTHON_SOURCE)

            # Analyze source tree
            await CodeAnalyzerService.run_analysis(
                project_id=project_id,
                root_dir=temp_dir,
                project_name="Sentinel-Core-Project",
                profile_metadata=project.metadata,
            )

        # 4. Invoke GET /api/v1/analysis/{project_id}/system-model
        res = client.get(f"/api/v1/analysis/{project_id}/system-model")
        assert res.status_code == 200
        json_body = res.json()
        assert json_body["success"] is True

        model_dict = json_body["data"]
        # Validate Structure
        assert model_dict["project_id"] == str(project_id)
        assert model_dict["project_name"] == "Sentinel-Core-Project"
        assert model_dict["total_files"] >= 1
        assert model_dict["total_classes"] >= 1
        assert model_dict["total_functions"] >= 3
        assert model_dict["total_requirements"] == 2
        assert model_dict["total_links"] >= 2

        # Check cross-referenced APIs and Dependencies
        assert len(model_dict["apis"]) == 1
        assert model_dict["apis"][0]["path"] == "/api/v1/auth/login"
        assert "production" in model_dict["dependencies"]

        # Check Requirement mappings
        mapping_ids = [m["requirement_identifier"] for m in model_dict["mappings"]]
        assert "REQ-AUTH-001" in mapping_ids
        assert "REQ-SEC-002" in mapping_ids

        # Validate with SoftwareSystemModel Pydantic model
        system_model = SoftwareSystemModel.model_validate(model_dict)
        assert system_model.project_id == project_id

    def test_analysis_post_job_trigger(self, client: TestClient):
        """Verify POST /api/v1/analysis triggers non-blocking background job (HTTP 202)."""
        project_id = str(uuid.uuid4())
        res = client.post("/api/v1/analysis", json={"project_id": project_id})
        assert res.status_code == 202
        body = res.json()
        assert body["success"] is True
        assert body["data"]["job_id"] is not None

    def test_requirements_post_job_trigger(self, client: TestClient):
        """Verify POST /api/v1/requirements ingests raw requirements (HTTP 202)."""
        project_id = str(uuid.uuid4())
        res = client.post(
            "/api/v1/requirements",
            json={"project_id": project_id, "text": STRUCTURED_SRS_MARKDOWN},
        )
        assert res.status_code == 202
        body = res.json()
        assert body["success"] is True
        assert len(body["data"]) == 2
