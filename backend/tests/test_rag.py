"""
Unit & Integration Tests for Module 3 Part B: Qdrant RAG.

Covers:
4. Cross-Project Leakage Test: Index Project A & Project B separately, query Project A -> assert zero leakage from Project B.
5. Chunking Test: Assert a known function/class is chunked as a single coherent unit, not split mid-function.
6. Context Builder Test: Assert combined output includes both vector hits AND graph traversals.
"""

import pytest

from app.knowledge_graph.service import KnowledgeGraphService
from app.rag.chunker import CodeChunker
from app.rag.models import ChunkType, RAGCollection
from app.rag.service import RAGService
from tests.fixtures.knowledge.sample_system_models import (
    PROJECT_A_ID,
    PROJECT_B_ID,
    SAMPLE_SYSTEM_MODEL_PROJECT_A,
    SAMPLE_SYSTEM_MODEL_PROJECT_B,
)


@pytest.mark.asyncio
class TestRAGPipeline:
    """Test Suite for Vector Indexing, Chunking, Multi-Tenant Isolation, and Hybrid Context Assembly."""

    async def test_04_cross_project_leakage_prevention(self):
        """
        4. Cross-Project Leakage Test:
        Index fixture content for Project A and Project B separately, then querying with Project A's
        project_id -> assert results NEVER include Project B's vectors.
        """
        # 1. Index Project A (Auth)
        res_a = await RAGService.index_project_content(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )
        assert res_a["total_chunks_indexed"] > 0

        # 2. Index Project B (Payment / Stripe)
        res_b = await RAGService.index_project_content(
            project_id=PROJECT_B_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_B
        )
        assert res_b["total_chunks_indexed"] > 0

        # 3. Query with Project A's ID for payment/stripe terms that ONLY exist in Project B
        context_a = await RAGService.query_context(
            project_id=PROJECT_A_ID,
            query="process_charge credit card stripe payment",
            top_k=10
        )

        # Assert Project A's results NEVER contain Project B chunks or IDs
        for hit in (context_a.code_results + context_a.requirement_results + context_a.test_results):
            assert hit.project_id == PROJECT_A_ID
            assert "stripe" not in hit.title.lower()
            assert "payment" not in hit.title.lower()
            assert "process_charge" not in hit.title.lower()

        # 4. Now query with Project B's ID for the same terms -> MUST find Project B chunks
        context_b = await RAGService.query_context(
            project_id=PROJECT_B_ID,
            query="process_charge credit card stripe payment",
            top_k=10
        )

        found_b_hits = [
            h for h in (context_b.code_results + context_b.requirement_results + context_b.test_results)
            if h.project_id == PROJECT_B_ID
        ]
        assert len(found_b_hits) > 0
        assert any("charge" in h.title.lower() or "stripe" in h.title.lower() for h in found_b_hits)

    async def test_05_ast_boundary_chunking_coherence(self):
        """
        5. Chunking Test:
        Assert a known function/class is chunked as a single coherent unit, not split mid-function.
        """
        chunks = CodeChunker.chunk_system_model(
            project_id=PROJECT_A_ID,
            system_model=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        # Find the authenticate_user function chunk
        auth_fn_chunks = [
            c for c in chunks
            if c.chunk_type == ChunkType.FUNCTION and "authenticate_user" in c.title
        ]

        assert len(auth_fn_chunks) == 1, "authenticate_user should be exactly one chunk, not split."
        chunk = auth_fn_chunks[0]

        # Verify chunk coherence: contains signature, docstring, and complete logic
        assert "Function: app.services.auth_service.AuthenticationService.authenticate_user" in chunk.content
        assert "Docstring: Verify credentials against user database" in chunk.content
        assert "def authenticate_user" in chunk.content
        assert "return {'token': token, 'username': username}" in chunk.content
        assert chunk.file_path == "app/services/auth_service.py"
        assert chunk.start_line == 15
        assert chunk.end_line == 28

        # Verify Requirement chunk: exactly 1 chunk per requirement
        req_chunks = [c for c in chunks if c.chunk_type == ChunkType.REQUIREMENT]
        assert len(req_chunks) == 2
        req1 = [r for r in req_chunks if "REQ-AUTH-001" in r.title][0]
        assert "Acceptance Criteria:" in req1.content
        assert "Valid credentials return 200 with JWT access token." in req1.content

    async def test_06_hybrid_context_builder_combines_vector_and_graph(self):
        """
        6. Context Builder Test:
        Assert the combined output includes BOTH vector-search hits AND graph-traversal results.
        """
        # Ensure graph is built for Project A
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )
        # Ensure vectors are indexed for Project A
        await RAGService.index_project_content(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        # Query that invokes both vector matching and graph traversal
        context = await RAGService.query_context(
            project_id=PROJECT_A_ID,
            query="How does authenticate_user work and what tests verify it?",
            top_k=5
        )

        # 1. Assert Vector Search Hits exist
        assert context.total_hits > 0
        assert len(context.code_results) > 0 or len(context.requirement_results) > 0

        # 2. Assert Graph Traversal Results exist in graph_context
        assert "call_neighborhoods" in context.graph_context
        call_neighborhoods = context.graph_context["call_neighborhoods"]
        assert len(call_neighborhoods) > 0

        # Assert callers/callees were extracted from Neo4j
        assert any(cn.get("target_function") == "authenticate_user" for cn in call_neighborhoods)

        # 3. Assert verifiable evidence citations were populated
        assert len(context.evidence_citations) > 0
        citations = set(context.evidence_citations)
        assert any("authenticate_user" in c for c in citations)
        assert any("REQ-AUTH-001" in c or "REQ-AUTH-002" in c for c in citations)
