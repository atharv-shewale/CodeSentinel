"""
Unit & Integration Tests for Module 3 Part A: Neo4j Knowledge Graph.

Covers:
1. Loading a fixture Software System Model into Neo4j -> assert exact expected nodes and relationships exist.
2. Re-running the load for the same project_id -> assert no duplicate nodes are created (idempotency/MERGE verified).
3. Each of the four named query types:
   - Untested requirements
   - Functions related to a given failure
   - Files changed by a commit and dependent tests
   - Call graph neighborhood of a function
"""

import pytest
import uuid

from app.knowledge_graph.client import neo4j_client
from app.knowledge_graph.models import GraphNodeType, GraphRelationshipType
from app.knowledge_graph.service import KnowledgeGraphService
from tests.fixtures.knowledge.sample_system_models import (
    PROJECT_A_ID,
    SAMPLE_SYSTEM_MODEL_PROJECT_A,
)


@pytest.mark.asyncio
class TestKnowledgeGraphMaterialization:
    """Test Suite for Knowledge Graph Materialization, Stale-Data Policy, and Named Traversals."""

    async def test_01_load_fixture_system_model_into_graph(self):
        """1. Loading a fixture Software System Model into Neo4j -> assert exact expected nodes and relationships exist."""
        # Materialize Project A into graph
        topo = await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        assert topo.project_id == PROJECT_A_ID
        assert topo.total_nodes > 0
        assert topo.total_edges > 0

        node_types = {n.entity_type for n in topo.nodes}
        # Assert expected node types exist
        assert GraphNodeType.PROJECT.value in node_types
        assert GraphNodeType.FILE.value in node_types
        assert GraphNodeType.CLASS.value in node_types
        assert GraphNodeType.FUNCTION.value in node_types
        assert GraphNodeType.REQUIREMENT.value in node_types
        assert GraphNodeType.TEST.value in node_types
        assert GraphNodeType.EXECUTION.value in node_types
        assert GraphNodeType.FAILURE.value in node_types
        assert GraphNodeType.FINDING.value in node_types
        assert GraphNodeType.COMMIT.value in node_types

        # Assert specific node counts
        file_nodes = [n for n in topo.nodes if n.entity_type == GraphNodeType.FILE.value]
        fn_nodes = [n for n in topo.nodes if n.entity_type == GraphNodeType.FUNCTION.value]
        req_nodes = [n for n in topo.nodes if n.entity_type == GraphNodeType.REQUIREMENT.value]
        test_nodes = [n for n in topo.nodes if n.entity_type == GraphNodeType.TEST.value]

        assert len(file_nodes) == 3
        assert len(fn_nodes) == 3
        assert len(req_nodes) == 2
        assert len(test_nodes) == 1

        # Assert relationships exist
        rel_types = {e.relationship for e in topo.edges}
        assert GraphRelationshipType.PROJECT_CONTAINS_FILE.value in rel_types
        assert GraphRelationshipType.FUNCTION_CALLS_FUNCTION.value in rel_types
        assert GraphRelationshipType.REQUIREMENT_IMPLEMENTED_BY_FUNCTION.value in rel_types
        assert GraphRelationshipType.REQUIREMENT_TESTED_BY_TEST.value in rel_types
        assert GraphRelationshipType.EXECUTION_PRODUCED_FAILURE.value in rel_types
        assert GraphRelationshipType.FAILURE_RELATED_TO_FUNCTION.value in rel_types
        assert GraphRelationshipType.COMMIT_MODIFIES_FILE.value in rel_types

    async def test_02_idempotent_reloading_creates_no_duplicate_nodes(self):
        """2. Re-running the load for the same project_id -> assert no duplicate nodes are created (idempotency/MERGE behavior)."""
        # Run first load
        topo1 = await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )
        initial_node_count = topo1.total_nodes
        initial_edge_count = topo1.total_edges

        # Run second load (re-index simulation)
        topo2 = await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        assert topo2.total_nodes == initial_node_count
        assert topo2.total_edges == initial_edge_count

        # Node IDs must be unique
        node_ids = [n.id for n in topo2.nodes]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs detected after reload!"

    async def test_03_query_untested_requirements(self):
        """3a. Named Traversal: 'requirements with no linked test'."""
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        untested = await KnowledgeGraphService.get_untested_requirements(PROJECT_A_ID)
        assert len(untested) == 1
        assert untested[0].identifier == "REQ-AUTH-002"
        assert untested[0].title == "Multi-Factor Authentication Check"
        assert len(untested[0].linked_functions) >= 1

    async def test_03_query_failure_related_functions(self):
        """3b. Named Traversal: 'functions related to a given failure'."""
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        fail_id = f"{PROJECT_A_ID}-fail-001"
        failures = await KnowledgeGraphService.get_failure_related_functions(
            project_id=PROJECT_A_ID,
            failure_id=fail_id
        )

        assert len(failures) == 1
        assert failures[0].failure_id == fail_id
        assert len(failures[0].related_functions) == 2
        fn_names = {f["name"] for f in failures[0].related_functions}
        assert "authenticate_user" in fn_names
        assert "generate_access_token" in fn_names

    async def test_03_query_commit_impact_and_tests(self):
        """3c. Named Traversal: 'files changed by a commit and their dependent tests'."""
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        commit_hash = "c0ffee1234567890abcdef1234567890abcdef12"
        impacts = await KnowledgeGraphService.get_commit_impact_and_tests(
            project_id=PROJECT_A_ID,
            commit_hash=commit_hash
        )

        assert len(impacts) == 1
        assert impacts[0].commit_hash == commit_hash
        assert len(impacts[0].modified_files) >= 1
        assert len(impacts[0].impacted_functions) >= 1
        assert "test_authenticate_user_success" in impacts[0].dependent_tests

    async def test_03_query_call_neighborhood(self):
        """3d. Named Traversal: 'call graph neighborhood of a function'."""
        await KnowledgeGraphService.build_graph_for_project(
            project_id=PROJECT_A_ID,
            system_model_override=SAMPLE_SYSTEM_MODEL_PROJECT_A
        )

        neighborhoods = await KnowledgeGraphService.get_call_neighborhood(
            project_id=PROJECT_A_ID,
            function_name="authenticate_user",
            depth=1
        )

        assert len(neighborhoods) >= 1
        target_item = neighborhoods[0]
        assert target_item.target_function == "authenticate_user"
        # authenticate_user calls generate_access_token
        assert any("generate_access_token" in c for c in target_item.callees)
