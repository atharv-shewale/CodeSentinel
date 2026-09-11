"""
Integration Tests for Module 3 API Routes: Knowledge Graph, RAG, and AI Agents.

Verifies:
1. Universal APIResponse envelope compliance across all endpoints.
2. POST /api/v1/knowledge/{project_id}/build & GET /api/v1/knowledge/{project_id}/query
3. POST /api/v1/rag/{project_id}/index & POST /api/v1/rag/{project_id}/query
4. POST /api/v1/agents/{project_id}/ask
5. Typed error responses for uninitialized / unindexed projects.
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from app.knowledge_graph.service import KnowledgeGraphService
from app.main import app
from app.rag.service import RAGService
from tests.fixtures.knowledge.sample_system_models import (
    PROJECT_A_ID,
    SAMPLE_SYSTEM_MODEL_PROJECT_A,
)

client = TestClient(app)


class TestModule3APIRoutes:
    """Tests for Module 3 REST API endpoints and universal response envelope."""

    @pytest.fixture(autouse=True)
    def setup_project_a(self):
        """Pre-populate Project A in Knowledge Graph & RAG before each route test."""
        import asyncio
        asyncio.run(KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        ))
        asyncio.run(RAGService.index_project_content(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        ))

    def test_knowledge_graph_build_endpoint(self):
        """POST /api/v1/knowledge/{project_id}/build returns 202 with JobStatus inside APIResponse."""
        test_proj = str(uuid.uuid4())
        resp = client.post(f"/api/v1/knowledge/{test_proj}/build")
        assert resp.status_code == 202
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] in ["PENDING", "RUNNING", "COMPLETED"]
        assert "timestamp" in body

    def test_knowledge_graph_query_untested_requirements(self):
        """GET /api/v1/knowledge/{project_id}/query?query_type=untested_requirements."""
        resp = client.get(f"/api/v1/knowledge/{PROJECT_A_ID}/query?query_type=untested_requirements")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["query_type"] == "untested_requirements"
        assert body["data"]["total_results"] >= 1
        assert len(body["data"]["untested_requirements"]) >= 1

    def test_knowledge_graph_query_call_neighborhood(self):
        """GET /api/v1/knowledge/{project_id}/query?query_type=call_neighborhood&function_name=authenticate_user."""
        resp = client.get(f"/api/v1/knowledge/{PROJECT_A_ID}/query?query_type=call_neighborhood&function_name=authenticate_user")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["query_type"] == "call_neighborhood"
        assert body["data"]["total_results"] >= 1

    def test_knowledge_graph_topology_endpoint(self):
        """GET /api/v1/knowledge/graph/{project_id} returns topology nodes and edges."""
        resp = client.get(f"/api/v1/knowledge/graph/{PROJECT_A_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total_nodes"] > 0
        assert body["data"]["total_edges"] > 0

    def test_rag_index_endpoint(self):
        """POST /api/v1/rag/{project_id}/index returns 202 with JobStatus."""
        resp = client.post(f"/api/v1/rag/{PROJECT_A_ID}/index")
        assert resp.status_code == 202
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["status"] in ["PENDING", "RUNNING", "COMPLETED"]

    def test_rag_query_endpoint(self):
        """POST /api/v1/rag/{project_id}/query returns assembled RAGContext."""
        payload = {"query": "How is authentication handled?", "top_k": 5}
        resp = client.post(f"/api/v1/rag/{PROJECT_A_ID}/query", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["project_id"] == PROJECT_A_ID
        assert "evidence_citations" in data
        assert "graph_context" in data

    def test_agents_ask_endpoint_grounded(self):
        """POST /api/v1/agents/{project_id}/ask returns grounded response."""
        payload = {
            "question": "How does authenticate_user in auth_service.py implement REQ-AUTH-001?",
            "agent_type": "CODE_AGENT",
            "top_k": 5
        }
        resp = client.post(f"/api/v1/agents/{PROJECT_A_ID}/ask", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["project_id"] == PROJECT_A_ID
        assert data["agent_type"] == "CODE_AGENT"
        assert data["is_grounded"] is True
        assert len(data["cited_evidence"]) >= 1

    def test_uninitialized_project_returns_typed_error(self):
        """Querying a non-existent project returns a clear typed error envelope."""
        random_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/knowledge/{random_id}/query?query_type=untested_requirements")
        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "GRAPH_NOT_INITIALIZED"
        assert "build" in body["error"]["message"]
