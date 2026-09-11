"""
CodeSentinel Module 4 Tests: API Endpoints & Error Handling.

Verifies:
- POST /api/v1/tests/{project_id}/generate with missing analysis data returns ANALYSIS_NOT_FOUND (404).
- POST /api/v1/tests/{project_id}/generate with analysis data returns 200/202 and TestCase list.
- POST /api/v1/executions/{project_id}/run with Docker down returns DOCKER_UNAVAILABLE (503).
- GET /api/v1/tests/{project_id} lists tests for project.
- GET /api/v1/failures/{project_id} lists failures for project.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from app.main import app

# Prevent pytest from attempting to collect imported schema classes as test suites
TestCase.__test__ = False
TestProvenance.__test__ = False
TestStatus.__test__ = False
TestType.__test__ = False


def test_generate_tests_missing_analysis_data(client: TestClient):
    """Verifies typed error ANALYSIS_NOT_FOUND (404) when generating tests for unanalyzed project."""
    project_id = uuid.uuid4()

    # Mock external client returning None for system model (Module 2 has not analyzed project)
    with patch("app.testing.client.ExternalServiceClient.get_system_model", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        res = client.post(
            f"/api/v1/tests/{project_id}/generate",
            json={"sync": True},
        )

        assert res.status_code == 404
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"
        assert "run analysis first" in body["error"]["message"].lower()


def test_generate_tests_with_analysis_data(client: TestClient):
    """Verifies successful test generation when Module 2 analysis data is present."""
    project_id = uuid.uuid4()
    req_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    mock_model = {
        "requirements": [
            {
                "id": str(req_id),
                "identifier": "REQ-1",
                "title": "Auth",
                "acceptance_criteria": ["Criteria 1"],
                "target_entity_ids": [str(entity_id)],
            }
        ],
        "entities": [{"id": str(entity_id), "name": "login_handler"}],
        "routes": [],
    }

    with patch("app.testing.client.ExternalServiceClient.get_system_model", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_model

        res = client.post(
            f"/api/v1/tests/{project_id}/generate",
            json={"sync": True, "tiers": ["REQUIREMENT_VERIFIED"]},
        )

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["provenance"] == "REQUIREMENT_VERIFIED"


def test_executions_docker_unavailable(client: TestClient):
    """Verifies typed error DOCKER_UNAVAILABLE (503) when Docker daemon is not accessible."""
    project_id = uuid.uuid4()

    with patch("app.sandbox.executor.DockerSandboxExecutor.is_docker_available", return_value=False):
        res = client.post(
            f"/api/v1/executions/{project_id}/run",
            json={"sync": True},
        )

        assert res.status_code == 503
        body = res.json()
        assert body["success"] is False
        assert body["error"]["code"] == "DOCKER_UNAVAILABLE"
        assert "unavailable" in body["error"]["message"].lower()


def test_get_project_tests_and_failures(client: TestClient):
    """Verifies GET endpoints for tests and failures."""
    project_id = uuid.uuid4()

    res_tests = client.get(f"/api/v1/tests/{project_id}")
    assert res_tests.status_code == 200
    assert "data" in res_tests.json()

    res_failures = client.get(f"/api/v1/failures/{project_id}")
    assert res_failures.status_code == 200
    assert "data" in res_failures.json()
