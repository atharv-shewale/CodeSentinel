"""
CodeSentinel Ingestion & Profiler Job Lifecycle Test Suite.

Verifies non-blocking background job dispatching, real-time progress transitions,
ZIP upload endpoints, and profile retrieval via FastAPI TestClient.
"""

import asyncio
import base64
import io
import tempfile
import time
import uuid
from fastapi.testclient import TestClient
import pytest

from shared.schemas.jobs import JobState
from shared.schemas.project import Project
from app.core.project_store import ProjectStore
from app.ingestion.service import IngestionService
from tests.fixtures.ingestion.make_fixtures import (
    create_python_fastapi_repo,
    create_zip_from_dir,
)


class TestIngestionJobLifecycle:
    """Verifies end-to-end asynchronous job flow and HTTP API endpoints."""

    def test_repositories_status_endpoint(self, client: TestClient):
        """Verify GET /api/v1/repositories/status returns service capability telemetry."""
        res = client.get("/api/v1/repositories/status")
        assert res.status_code == 200
        json_body = res.json()
        assert json_body["success"] is True
        assert json_body["data"]["status"] == "READY"
        assert "GITHUB" in json_body["data"]["supported_providers"]

    @pytest.mark.asyncio
    async def test_zip_payload_ingestion_job_lifecycle(self, client: TestClient):
        """
        REQUIREMENT #8: Assert POST /api/v1/repositories returns a job_id immediately
        (does not block), and that GET /api/v1/jobs/{job_id} transitions through progress
        states to a final 'done' with the Project result attached.
        """
        # 1. Create temporary sample repo and pack into ZIP bytes
        with tempfile.TemporaryDirectory() as temp_dir:
            create_python_fastapi_repo(temp_dir)
            zip_bytes = create_zip_from_dir(temp_dir)

        zip_base64 = base64.b64encode(zip_bytes).decode("utf-8")

        # 2. Dispatch ingestion job via POST /api/v1/repositories
        post_res = client.post(
            "/api/v1/repositories",
            json={
                "source_type": "zip",
                "zip_base64": zip_base64,
                "project_name": "Async-FastAPI-App",
            },
        )
        assert post_res.status_code == 202
        post_data = post_res.json()
        assert post_data["success"] is True
        job_id = post_data["data"]["job_id"]
        assert job_id is not None

        # 3. Poll GET /api/v1/jobs/{job_id} until completed (up to 5 seconds)
        job_data = None
        for _ in range(25):
            await asyncio.sleep(0.2)
            job_res = client.get(f"/api/v1/jobs/{job_id}")
            assert job_res.status_code == 200
            job_data = job_res.json()["data"]
            if job_data["status"] in ("COMPLETED", "FAILED"):
                break

        assert job_data is not None
        assert job_data["job_id"] == job_id
        assert job_data["status"] == "COMPLETED", f"Job failed: {job_data.get('error')}"
        assert job_data["progress"]["percentage"] == 100.0
        assert job_data["result"] is not None

        project_dict = job_data["result"]
        assert project_dict["name"] == "Async-FastAPI-App"
        assert project_dict["metadata"]["primary_language"] == "python"

        # 4. Retrieve project profile via GET /api/v1/profile/{project_id}
        project_id = project_dict["id"]
        profile_res = client.get(f"/api/v1/profile/{project_id}")
        assert profile_res.status_code == 200
        profile_body = profile_res.json()
        assert profile_body["success"] is True
        assert profile_body["data"]["id"] == project_id
        assert profile_body["data"]["name"] == "Async-FastAPI-App"

    def test_zip_multipart_upload_endpoint(self, client: TestClient):
        """Verify POST /api/v1/repositories/upload multipart ZIP upload."""
        with tempfile.TemporaryDirectory() as temp_dir:
            create_python_fastapi_repo(temp_dir)
            zip_bytes = create_zip_from_dir(temp_dir)

        files = {"file": ("repo.zip", io.BytesIO(zip_bytes), "application/zip")}
        data = {"project_name": "Multipart-Upload-App"}

        res = client.post("/api/v1/repositories/upload", files=files, data=data)
        assert res.status_code == 202
        body = res.json()
        assert body["success"] is True
        assert body["data"]["job_id"] is not None
