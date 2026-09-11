"""
Test Requirements Document Upload and Query End-to-End.

Validates FIX 1:
- POST /api/v1/requirements/upload returns HTTP 200 (not 500)
- JobType is valid (JobType.REQUIREMENTS_PARSING)
- Uploaded requirements are stored and queryable via GET /api/v1/requirements/{project_id}
"""

import asyncio
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from shared.schemas.jobs import JobType


@pytest.mark.asyncio
async def test_upload_requirements_document_returns_200_and_stores_entities(client: TestClient):
    project_id = str(uuid.uuid4())
    req_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_project", "requirements.md")
    assert os.path.exists(req_file_path), f"Sample requirements.md not found at {req_file_path}"

    with open(req_file_path, "rb") as f:
        file_bytes = f.read()

    # Upload requirements document
    response = client.post(
        "/api/v1/requirements/upload",
        data={"project_id": project_id},
        files={"file": ("requirements.md", file_bytes, "text/markdown")},
    )

    # Must return 200 OK (not 500 internal server error)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body.get("success") is True
    job_data = body.get("data", {})
    assert job_data.get("job_type") in ("REQUIREMENTS_PARSING", "REQUIREMENT_PARSING")

    # Allow the background parsing task to complete
    await asyncio.sleep(1.0)

    # Query requirements via GET endpoint
    query_res = client.get(f"/api/v1/requirements/{project_id}")
    assert query_res.status_code == 200
    query_body = query_res.json()
    assert query_body.get("success") is True
    stored_reqs = query_body.get("data", [])

    assert len(stored_reqs) >= 2, f"Expected stored requirements, got {len(stored_reqs)}"
    identifiers = [r["identifier"] for r in stored_reqs]
    assert "REQ-CALC-01" in identifiers, f"REQ-CALC-01 missing from stored requirements: {identifiers}"

    # Verify acceptance criteria for REQ-CALC-01 are intact
    calc_req = next(r for r in stored_reqs if r["identifier"] == "REQ-CALC-01")
    assert len(calc_req.get("acceptance_criteria", [])) == 2
    assert any("count_items" in ac for ac in calc_req["acceptance_criteria"])
