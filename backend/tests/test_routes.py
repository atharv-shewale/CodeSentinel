"""
CodeSentinel API Route Groups Tests.

Queries all 16 route groups and confirms they return valid APIResponse envelopes
with expected HTTP status codes.
"""

import uuid
from fastapi.testclient import TestClient


def test_system_health(client: TestClient):
    """Test root and healthcheck endpoints."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    json_root = res_root.json()
    assert json_root["success"] is True
    assert json_root["data"]["service"] == "CodeSentinel"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["success"] is True


def test_projects_route(client: TestClient):
    """Test /api/v1/projects endpoints."""
    res = client.get("/api/v1/projects")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Test POST
    post_res = client.post(
        "/api/v1/projects",
        json={
            "name": "E2E Test Repo",
            "repository_url": "https://github.com/test/repo.git",
            "default_branch": "main",
            "provider": "GITHUB",
            "tags": ["test"],
        }
    )
    assert post_res.status_code == 201
    assert post_res.json()["data"]["name"] == "E2E Test Repo"


def test_repositories_route(client: TestClient):
    """Test /api/v1/repositories endpoints."""
    res = client.get("/api/v1/repositories/status")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "READY"

    ingest_res = client.post(
        "/api/v1/repositories/ingest",
        json={"repository_url": "https://github.com/org/app.git", "branch": "main"}
    )
    assert ingest_res.status_code == 202
    assert ingest_res.json()["data"]["job_type"] == "REPO_INGESTION"


def test_requirements_route(client: TestClient):
    """Test /api/v1/requirements endpoints."""
    res = client.get("/api/v1/requirements")
    assert res.status_code == 200
    assert res.json()["success"] is True

    create_res = client.post(
        "/api/v1/requirements",
        json={
            "project_id": str(uuid.uuid4()),
            "identifier": "REQ-SEC-01",
            "title": "Data Encryption at Rest",
            "description": "All DB volumes encrypted with AES-256.",
            "req_type": "SECURITY",
            "priority": "CRITICAL",
            "acceptance_criteria": ["KMS key enabled"],
        }
    )
    assert create_res.status_code == 201
    assert create_res.json()["data"]["identifier"] == "REQ-SEC-01"


def test_profile_route(client: TestClient):
    """Test /api/v1/profile endpoints."""
    proj_id = str(uuid.uuid4())
    res_run = client.post("/api/v1/profile/run", json={"project_id": proj_id, "depth": "FULL"})
    assert res_run.status_code == 202

    res_get = client.get(f"/api/v1/profile/{proj_id}")
    assert res_get.status_code == 200
    data = res_get.json()["data"]
    primary_lang = data.get("primary_language") or data.get("metadata", {}).get("primary_language")
    assert primary_lang == "python"


def test_analysis_route(client: TestClient):
    """Test /api/v1/analysis endpoints (AST & Routes)."""
    proj_id = str(uuid.uuid4())
    res_ast = client.post("/api/v1/analysis/ast", json={"project_id": proj_id})
    assert res_ast.status_code == 202

    res_entities = client.get(f"/api/v1/analysis/entities/{proj_id}")
    assert res_entities.status_code == 200
    assert len(res_entities.json()["data"]) > 0

    res_routes = client.get(f"/api/v1/analysis/routes/{proj_id}")
    assert res_routes.status_code == 200
    assert len(res_routes.json()["data"]) > 0


def test_knowledge_graph_route(client: TestClient):
    """Test /api/v1/knowledge endpoints."""
    proj_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/knowledge/graph/{proj_id}")
    assert res.status_code == 200
    assert "nodes" in res.json()["data"]
    assert "edges" in res.json()["data"]


def test_rag_route(client: TestClient):
    """Test /api/v1/rag endpoints."""
    proj_id = str(uuid.uuid4())
    res_search = client.post(
        "/api/v1/rag/search",
        json={"project_id": proj_id, "query": "find authentication token handler", "top_k": 3}
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["data"]) > 0


def test_agents_route(client: TestClient):
    """Test /api/v1/agents endpoints."""
    proj_id = str(uuid.uuid4())
    res_orch = client.post(
        "/api/v1/agents/orchestrate",
        json={"project_id": proj_id, "goal": "GENERATE_TESTS"}
    )
    assert res_orch.status_code == 202

    res_run = client.get("/api/v1/agents/runs/run-99")
    assert res_run.status_code == 200
    assert res_run.json()["data"]["run_id"] == "run-99"


def test_tests_route(client: TestClient):
    """Test /api/v1/tests endpoints."""
    res_list = client.get("/api/v1/tests")
    assert res_list.status_code == 200
    assert res_list.json()["data"][0]["provenance"] in [
        "REQUIREMENT_VERIFIED", "SCHEMA_DERIVED", "COVERAGE_ONLY", "AI_INFERRED", "MUTATION_TARGETED"
    ]

    # Test generation trigger
    gen_res = client.post(
        "/api/v1/tests/generate",
        json={"project_id": str(uuid.uuid4()), "provenance_strategy": "REQUIREMENT_VERIFIED"}
    )
    assert gen_res.status_code == 202


def test_executions_route(client: TestClient):
    """Test /api/v1/executions endpoints."""
    exec_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/executions/{exec_id}")
    assert res.status_code == 200
    assert res.json()["data"]["environment"] == "DOCKER_SANDBOX"


def test_failures_route(client: TestClient):
    """Test /api/v1/failures endpoints."""
    res_list = client.get("/api/v1/failures")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) > 0

    fail_id = str(uuid.uuid4())
    res_rca = client.get(f"/api/v1/failures/{fail_id}/rca")
    assert res_rca.status_code == 200
    assert res_rca.json()["data"]["confidence_score"] > 0.9


def test_audits_route(client: TestClient):
    """Test /api/v1/audits endpoints."""
    proj_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/audits/findings/{proj_id}")
    assert res.status_code == 200
    assert res.json()["data"][0]["category"] == "SECURITY_VULNERABILITY"


def test_analytics_route(client: TestClient):
    """Test /api/v1/analytics endpoints."""
    proj_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/analytics/overview/{proj_id}")
    assert res.status_code == 200
    assert "health_score" in res.json()["data"]


def test_reports_route(client: TestClient):
    """Test /api/v1/reports endpoints."""
    res = client.get("/api/v1/reports/rep-12345")
    assert res.status_code == 200
    assert res.json()["data"]["report_id"] == "rep-12345"


def test_assistant_route(client: TestClient):
    """Test /api/v1/assistant endpoints."""
    res = client.post(
        "/api/v1/assistant/chat",
        json={
            "project_id": str(uuid.uuid4()),
            "messages": [{"role": "user", "content": "How do I audit my routes?"}]
        }
    )
    assert res.status_code == 200
    assert "reply" in res.json()["data"]


def test_jobs_route(client: TestClient):
    """Test /api/v1/jobs endpoints (Background job lifecycle)."""
    # 1. Enqueue test job
    create_res = client.post("/api/v1/jobs/test-job", json={"job_type": "AST_ANALYSIS", "total_steps": 20})
    assert create_res.status_code == 202
    job_data = create_res.json()["data"]
    job_id = job_data["job_id"]
    assert job_data["status"] == "PENDING"

    # 2. Query status
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["data"]["job_id"] == job_id

    # 3. Query non-existent job -> 404 error envelope
    missing_res = client.get("/api/v1/jobs/non-existent-uuid")
    assert missing_res.status_code == 404
    assert missing_res.json()["success"] is False
    assert missing_res.json()["error"]["code"] == "JOB_NOT_FOUND"
