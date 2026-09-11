"""
CodeSentinel Knowledge Graph Module: Service Layer.

Handles:
1. Fetching Software System Model from Module 2 API (GET /api/v1/analysis/{project_id}/system-model).
2. Applying Stale-Data Policy (full re-index deletion of existing project subgraph).
3. Idempotent materialization of nodes and relationships into Neo4j (using MERGE).
4. Providing the 4 named graph traversal queries as clean service functions.
"""

from typing import Any, Dict, List, Optional, Union
import uuid
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.knowledge_graph.client import neo4j_client
from app.knowledge_graph.models import (
    CallNeighborhoodItem,
    CommitImpactItem,
    FailureFunctionItem,
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationshipType,
    GraphTopologyResponse,
    UntestedRequirementItem,
)
from app.knowledge_graph import cypher_queries


class KnowledgeGraphService:
    """Service orchestrating Knowledge Graph materialization and traversals."""

    @classmethod
    async def fetch_system_model(cls, project_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Fetch Software System Model from Module 2 external endpoint.
        Does NOT import from backend/app/analyzer or backend/app/requirements directly.
        """
        pid_str = str(project_id)
        # First check local application client if running in-process or via HTTP
        try:
            from app.main import app
            from httpx import ASGITransport, AsyncClient

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.get(f"/api/v1/analysis/{pid_str}/system-model")
                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data")
                    if data:
                        return data
        except Exception as e:
            logger.debug(f"Direct ASGI call for system model failed: {e}. Falling back to default empty model.")

        return {
            "project_id": pid_str,
            "project_name": f"Project-{pid_str[:8]}",
            "files": [],
            "classes": [],
            "functions": [],
            "api_routes": [],
            "dependencies": [],
            "requirements": [],
            "test_cases": [],
            "failures": [],
            "findings": [],
            "commits": [],
        }

    @classmethod
    async def build_graph_for_project(
        cls,
        project_id: Union[str, uuid.UUID],
        system_model_override: Optional[Dict[str, Any]] = None,
    ) -> GraphTopologyResponse:
        """
        Materializes Software System Model into Neo4j Knowledge Graph.

        STALE-DATA POLICY (MVP):
        Since a project can be re-analyzed after a commit, we implement a full
        re-index strategy for this MVP — on re-load, we delete this project's
        existing subgraph and rebuild it fresh, rather than attempting incremental
        diffing. Incremental diffing is explicitly out of scope for this phase.
        """
        pid_str = str(project_id)
        logger.info(f"Materializing Knowledge Graph for project {pid_str}...")

        # 1. Fetch system model from Module 2 API unless override is provided
        system_model = system_model_override
        if not system_model:
            system_model = await cls.fetch_system_model(pid_str)

        # 2. Apply Stale-Data Policy: delete existing project subgraph first
        if neo4j_client.is_in_memory:
            neo4j_client.in_memory_store.purge_project(pid_str)
        else:
            await neo4j_client.execute_query(
                cypher_queries.DELETE_PROJECT_SUBGRAPH,
                {"project_id": pid_str}
            )

        # 3. Materialize Project Node
        project_name = system_model.get("project_name", f"Project-{pid_str[:8]}")
        repo_url = system_model.get("repository_url", "")
        default_branch = system_model.get("default_branch", "main")

        if neo4j_client.is_in_memory:
            neo4j_client.in_memory_store.upsert_node(
                project_id=pid_str,
                node_id=pid_str,
                label=GraphNodeType.PROJECT.value,
                properties={"name": project_name, "repository_url": repo_url, "default_branch": default_branch}
            )
        else:
            await neo4j_client.execute_query(
                cypher_queries.UPSERT_PROJECT_NODE,
                {"id": pid_str, "name": project_name, "repository_url": repo_url, "default_branch": default_branch}
            )

        # 4. Materialize Files & Project-CONTAINS->File
        files = system_model.get("files", [])
        for f in files:
            f_id = str(f.get("id") or f.get("path") or uuid.uuid4())
            f_path = f.get("path", "")
            f_lang = f.get("language", "python")
            f_name = f.get("name", f_path.split("/")[-1] if "/" in f_path else f_path)

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=f_id,
                    label=GraphNodeType.FILE.value,
                    properties={"path": f_path, "language": f_lang, "name": f_name}
                )
                neo4j_client.in_memory_store.upsert_edge(
                    project_id=pid_str,
                    source_id=pid_str,
                    target_id=f_id,
                    rel_type=GraphRelationshipType.PROJECT_CONTAINS_FILE.value
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_FILE_NODE,
                    {"id": f_id, "project_id": pid_str, "path": f_path, "language": f_lang, "name": f_name}
                )
                await neo4j_client.execute_query(
                    cypher_queries.REL_PROJECT_CONTAINS_FILE,
                    {"project_id": pid_str, "file_id": f_id}
                )

        # 5. Materialize Classes & File-CONTAINS->Class
        classes = system_model.get("classes", [])
        for c in classes:
            c_id = str(c.get("id") or c.get("qualified_name") or uuid.uuid4())
            c_name = c.get("name", "")
            c_qname = c.get("qualified_name", c_name)
            c_file = c.get("file_path") or (c.get("location", {}).get("file_path", "") if isinstance(c.get("location"), dict) else "")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=c_id,
                    label=GraphNodeType.CLASS.value,
                    properties={"name": c_name, "qualified_name": c_qname, "file_path": c_file}
                )
                if c_file:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=c_file,
                        target_id=c_id,
                        rel_type=GraphRelationshipType.FILE_CONTAINS_FUNCTION.value
                    )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_CLASS_NODE,
                    {"id": c_id, "project_id": pid_str, "name": c_name, "qualified_name": c_qname, "file_path": c_file}
                )
                if c_file:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_FILE_CONTAINS_CLASS,
                        {"project_id": pid_str, "file_id": c_file, "class_id": c_id}
                    )

        # 6. Materialize Functions & File-CONTAINS->Function
        functions = system_model.get("functions", [])
        for fn in functions:
            fn_id = str(fn.get("id") or fn.get("qualified_name") or uuid.uuid4())
            fn_name = fn.get("name", "")
            fn_qname = fn.get("qualified_name", fn_name)
            fn_file = fn.get("file_path") or (fn.get("location", {}).get("file_path", "") if isinstance(fn.get("location"), dict) else "")
            fn_ret = fn.get("return_type", "")
            fn_comp = float(fn.get("complexity_score", 1.0) or 1.0)

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=fn_id,
                    label=GraphNodeType.FUNCTION.value,
                    properties={
                        "name": fn_name,
                        "qualified_name": fn_qname,
                        "file_path": fn_file,
                        "return_type": fn_ret,
                        "complexity_score": fn_comp,
                    }
                )
                if fn_file:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=fn_file,
                        target_id=fn_id,
                        rel_type=GraphRelationshipType.FILE_CONTAINS_FUNCTION.value
                    )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_FUNCTION_NODE,
                    {
                        "id": fn_id,
                        "project_id": pid_str,
                        "name": fn_name,
                        "qualified_name": fn_qname,
                        "file_path": fn_file,
                        "return_type": fn_ret,
                        "complexity_score": fn_comp,
                    }
                )
                if fn_file:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_FILE_CONTAINS_FUNCTION,
                        {"project_id": pid_str, "file_id": fn_file, "function_id": fn_id}
                    )

        # 7. Materialize Function-CALLS->Function
        call_graph = system_model.get("dependencies", []) or system_model.get("call_graph", [])
        for call in call_graph:
            caller_id = str(call.get("caller") or call.get("caller_id") or call.get("source") or "")
            callee_id = str(call.get("callee") or call.get("callee_id") or call.get("target") or "")
            if caller_id and callee_id:
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=caller_id,
                        target_id=callee_id,
                        rel_type=GraphRelationshipType.FUNCTION_CALLS_FUNCTION.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_FUNCTION_CALLS_FUNCTION,
                        {"project_id": pid_str, "caller_id": caller_id, "callee_id": callee_id}
                    )

        # 8. Materialize Requirements & Requirement-IMPLEMENTED_BY->Function
        requirements = system_model.get("requirements", [])
        for req in requirements:
            req_id = str(req.get("id") or req.get("identifier") or uuid.uuid4())
            identifier = req.get("identifier", "REQ-UNKNOWN")
            title = req.get("title", "")
            description = req.get("description", "")
            req_type = req.get("req_type", "FUNCTIONAL")
            priority = req.get("priority", "MEDIUM")
            status_val = req.get("status", "DRAFT")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=req_id,
                    label=GraphNodeType.REQUIREMENT.value,
                    properties={
                        "identifier": identifier,
                        "title": title,
                        "description": description,
                        "req_type": req_type,
                        "priority": priority,
                        "status": status_val,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_REQUIREMENT_NODE,
                    {
                        "id": req_id,
                        "project_id": pid_str,
                        "identifier": identifier,
                        "title": title,
                        "description": description,
                        "req_type": req_type,
                        "priority": priority,
                        "status": status_val,
                    }
                )

            # Link implemented_by functions
            linked_fns = req.get("linked_entity_ids", []) or req.get("implemented_by", [])
            for fn_ref in linked_fns:
                fn_ref_id = str(fn_ref)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=req_id,
                        target_id=fn_ref_id,
                        rel_type=GraphRelationshipType.REQUIREMENT_IMPLEMENTED_BY_FUNCTION.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_REQUIREMENT_IMPLEMENTED_BY_FUNCTION,
                        {"project_id": pid_str, "requirement_id": req_id, "function_id": fn_ref_id}
                    )

        # 9. Materialize Tests & Requirement-TESTED_BY->Test
        tests = system_model.get("test_cases", []) or system_model.get("tests", [])
        for t in tests:
            t_id = str(t.get("id") or t.get("name") or uuid.uuid4())
            t_name = t.get("name", "")
            t_prov = t.get("provenance", "REQUIREMENT_VERIFIED")
            t_type = t.get("test_type", "UNIT")
            t_file = t.get("file_path", "")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=t_id,
                    label=GraphNodeType.TEST.value,
                    properties={
                        "name": t_name,
                        "provenance": t_prov,
                        "test_type": t_type,
                        "file_path": t_file,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_TEST_NODE,
                    {
                        "id": t_id,
                        "project_id": pid_str,
                        "name": t_name,
                        "provenance": t_prov,
                        "test_type": t_type,
                        "file_path": t_file,
                    }
                )

            # Link to requirement if specified
            req_ref = t.get("requirement_id")
            if req_ref:
                req_ref_id = str(req_ref)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=req_ref_id,
                        target_id=t_id,
                        rel_type=GraphRelationshipType.REQUIREMENT_TESTED_BY_TEST.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_REQUIREMENT_TESTED_BY_TEST,
                        {"project_id": pid_str, "requirement_id": req_ref_id, "test_id": t_id}
                    )

        # 10. Materialize Executions & Test-EXECUTED_AS->Execution
        executions = system_model.get("executions", [])
        for exc in executions:
            e_id = str(exc.get("id") or uuid.uuid4())
            e_status = exc.get("status", "PASSED")
            e_env = exc.get("environment", "DOCKER_SANDBOX")
            total_t = int(exc.get("total_tests", 0))
            passed_t = int(exc.get("passed_tests", 0))
            failed_t = int(exc.get("failed_tests", 0))

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=e_id,
                    label=GraphNodeType.EXECUTION.value,
                    properties={
                        "status": e_status,
                        "environment": e_env,
                        "total_tests": total_t,
                        "passed_tests": passed_t,
                        "failed_tests": failed_t,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_EXECUTION_NODE,
                    {
                        "id": e_id,
                        "project_id": pid_str,
                        "status": e_status,
                        "environment": e_env,
                        "total_tests": total_t,
                        "passed_tests": passed_t,
                        "failed_tests": failed_t,
                    }
                )

            # Link test to execution if test_case_id exists
            test_case_id = exc.get("test_case_id")
            if test_case_id:
                t_ref_id = str(test_case_id)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=t_ref_id,
                        target_id=e_id,
                        rel_type=GraphRelationshipType.TEST_EXECUTED_AS_EXECUTION.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_TEST_EXECUTED_AS_EXECUTION,
                        {"project_id": pid_str, "test_id": t_ref_id, "execution_id": e_id}
                    )

        # 11. Materialize Failures & Execution-PRODUCED->Failure & Failure-RELATED_TO->Function
        failures = system_model.get("failures", [])
        for f in failures:
            f_id = str(f.get("id") or uuid.uuid4())
            f_title = f.get("title", "")
            f_err = f.get("error_message", "")
            f_cat = f.get("category", "UNKNOWN")
            f_sev = f.get("severity", "MAJOR")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=f_id,
                    label=GraphNodeType.FAILURE.value,
                    properties={
                        "title": f_title,
                        "error_message": f_err,
                        "category": f_cat,
                        "severity": f_sev,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_FAILURE_NODE,
                    {
                        "id": f_id,
                        "project_id": pid_str,
                        "title": f_title,
                        "error_message": f_err,
                        "category": f_cat,
                        "severity": f_sev,
                    }
                )

            # Link from Execution
            exec_id = f.get("execution_id")
            if exec_id:
                e_ref = str(exec_id)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=e_ref,
                        target_id=f_id,
                        rel_type=GraphRelationshipType.EXECUTION_PRODUCED_FAILURE.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_EXECUTION_PRODUCED_FAILURE,
                        {"project_id": pid_str, "execution_id": e_ref, "failure_id": f_id}
                    )

            # Link to related functions
            rel_fns = f.get("related_functions", []) or f.get("target_entity_ids", [])
            for fn_ref in rel_fns:
                fn_ref_id = str(fn_ref)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=f_id,
                        target_id=fn_ref_id,
                        rel_type=GraphRelationshipType.FAILURE_RELATED_TO_FUNCTION.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_FAILURE_RELATED_TO_FUNCTION,
                        {"project_id": pid_str, "failure_id": f_id, "function_id": fn_ref_id}
                    )

        # 12. Materialize Commits & Commit-MODIFIES->File
        commits = system_model.get("commits", [])
        for cm in commits:
            cm_id = str(cm.get("id") or cm.get("commit_hash") or uuid.uuid4())
            cm_hash = cm.get("commit_hash", cm_id)
            cm_msg = cm.get("message", "")
            cm_auth = cm.get("author", "")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=cm_id,
                    label=GraphNodeType.COMMIT.value,
                    properties={
                        "commit_hash": cm_hash,
                        "message": cm_msg,
                        "author": cm_auth,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_COMMIT_NODE,
                    {
                        "id": cm_id,
                        "project_id": pid_str,
                        "commit_hash": cm_hash,
                        "message": cm_msg,
                        "author": cm_auth,
                    }
                )

            # Link modified files
            mod_files = cm.get("modified_files", [])
            for file_ref in mod_files:
                file_ref_id = str(file_ref)
                if neo4j_client.is_in_memory:
                    neo4j_client.in_memory_store.upsert_edge(
                        project_id=pid_str,
                        source_id=cm_id,
                        target_id=file_ref_id,
                        rel_type=GraphRelationshipType.COMMIT_MODIFIES_FILE.value
                    )
                else:
                    await neo4j_client.execute_query(
                        cypher_queries.REL_COMMIT_MODIFIES_FILE,
                        {"project_id": pid_str, "commit_id": cm_id, "file_id": file_ref_id}
                    )

        # 13. Materialize Findings (Security & Code Smell)
        findings = system_model.get("findings", [])
        for find in findings:
            find_id = str(find.get("id") or uuid.uuid4())
            find_rule = find.get("rule_id", "GENERAL")
            find_title = find.get("title", "")
            find_cat = find.get("category", "CODE_SMELL")
            find_sev = find.get("severity", "MEDIUM")

            if neo4j_client.is_in_memory:
                neo4j_client.in_memory_store.upsert_node(
                    project_id=pid_str,
                    node_id=find_id,
                    label=GraphNodeType.FINDING.value,
                    properties={
                        "rule_id": find_rule,
                        "title": find_title,
                        "category": find_cat,
                        "severity": find_sev,
                    }
                )
            else:
                await neo4j_client.execute_query(
                    cypher_queries.UPSERT_FINDING_NODE,
                    {
                        "id": find_id,
                        "project_id": pid_str,
                        "rule_id": find_rule,
                        "title": find_title,
                        "category": find_cat,
                        "severity": find_sev,
                    }
                )

        return await cls.get_project_topology(pid_str)

    # -------------------------------------------------------------------------
    # Traversal Query Methods (Internal Services, no raw Cypher leaked)
    # -------------------------------------------------------------------------

    @classmethod
    async def get_project_topology(cls, project_id: Union[str, uuid.UUID]) -> GraphTopologyResponse:
        """Retrieve the materialized node and edge topology for a project."""
        pid_str = str(project_id)
        if neo4j_client.is_in_memory:
            topo = neo4j_client.in_memory_store.get_topology(pid_str)
            nodes = [GraphNode(**n) for n in topo["nodes"]]
            edges = [GraphEdge(**e) for e in topo["edges"]]
            return GraphTopologyResponse(
                project_id=pid_str,
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
            )
        else:
            records = await neo4j_client.execute_query(
                cypher_queries.QUERY_PROJECT_TOPOLOGY,
                {"project_id": pid_str}
            )
            # Parse records into nodes and edges
            node_map: Dict[str, GraphNode] = {}
            edge_list: List[GraphEdge] = []
            for rec in records:
                n = rec.get("n")
                if n:
                    nid = n.get("id") or str(n.element_id)
                    labels = list(n.labels) if hasattr(n, "labels") else ["Node"]
                    props = dict(n)
                    node_map[nid] = GraphNode(
                        id=nid,
                        label=props.get("name") or props.get("identifier") or nid,
                        entity_type=labels[0] if labels else "Node",
                        properties=props,
                    )
                r = rec.get("r")
                m = rec.get("m")
                if r and n and m:
                    nid = n.get("id") or str(n.element_id)
                    mid = m.get("id") or str(m.element_id)
                    edge_list.append(GraphEdge(
                        source=nid,
                        target=mid,
                        relationship=r.type if hasattr(r, "type") else "RELATED_TO",
                        properties=dict(r) if hasattr(r, "__iter__") else {},
                    ))

            nodes = list(node_map.values())
            return GraphTopologyResponse(
                project_id=pid_str,
                nodes=nodes,
                edges=edge_list,
                total_nodes=len(nodes),
                total_edges=len(edge_list),
            )

    @classmethod
    async def get_untested_requirements(cls, project_id: Union[str, uuid.UUID]) -> List[UntestedRequirementItem]:
        """Query 1: Requirements with no linked test."""
        pid_str = str(project_id)
        if neo4j_client.is_in_memory:
            data = neo4j_client.in_memory_store.query_untested_requirements(pid_str)
            return [UntestedRequirementItem(**item) for item in data]
        else:
            records = await neo4j_client.execute_query(
                cypher_queries.QUERY_UNTESTED_REQUIREMENTS,
                {"project_id": pid_str}
            )
            return [UntestedRequirementItem(**rec) for rec in records]

    @classmethod
    async def get_failure_related_functions(
        cls,
        project_id: Union[str, uuid.UUID],
        failure_id: Optional[str] = None,
    ) -> List[FailureFunctionItem]:
        """Query 2: Functions related to a given failure."""
        pid_str = str(project_id)
        if neo4j_client.is_in_memory:
            data = neo4j_client.in_memory_store.query_failure_related_functions(pid_str, failure_id=failure_id)
            return [FailureFunctionItem(**item) for item in data]
        else:
            records = await neo4j_client.execute_query(
                cypher_queries.QUERY_FAILURE_RELATED_FUNCTIONS,
                {"project_id": pid_str, "failure_id": failure_id}
            )
            return [FailureFunctionItem(**rec) for rec in records]

    @classmethod
    async def get_commit_impact_and_tests(
        cls,
        project_id: Union[str, uuid.UUID],
        commit_hash: Optional[str] = None,
    ) -> List[CommitImpactItem]:
        """Query 3: Files changed by a commit and their dependent tests."""
        pid_str = str(project_id)
        if neo4j_client.is_in_memory:
            data = neo4j_client.in_memory_store.query_commit_impact(pid_str, commit_hash=commit_hash)
            return [CommitImpactItem(**item) for item in data]
        else:
            records = await neo4j_client.execute_query(
                cypher_queries.QUERY_COMMIT_IMPACT_AND_TESTS,
                {"project_id": pid_str, "commit_hash": commit_hash}
            )
            return [CommitImpactItem(**rec) for rec in records]

    @classmethod
    async def get_call_neighborhood(
        cls,
        project_id: Union[str, uuid.UUID],
        function_name: str,
        depth: int = 1,
    ) -> List[CallNeighborhoodItem]:
        """Query 4: Call graph neighborhood of a function."""
        pid_str = str(project_id)
        if neo4j_client.is_in_memory:
            data = neo4j_client.in_memory_store.query_call_neighborhood(pid_str, function_name=function_name, depth=depth)
            return [CallNeighborhoodItem(**item) for item in data]
        else:
            records = await neo4j_client.execute_query(
                cypher_queries.QUERY_CALL_NEIGHBORHOOD,
                {"project_id": pid_str, "function_name": function_name}
            )
            return [CallNeighborhoodItem(**rec) for rec in records]
