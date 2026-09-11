"""
CodeSentinel Knowledge Graph Module: Neo4j Database Client.

Provides async driver management, connection pooling, transactional query execution,
and an in-memory fallback graph store for isolated testing.
"""

from typing import Any, Dict, List, Optional
import uuid
from app.core.config import settings
from app.core.logging import logger

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncGraphDatabase = None
    AsyncDriver = None


class InMemoryGraphStore:
    """
    In-memory graph database simulator for unit testing and offline development.
    Supports node creation/upsert, relationship linking, and the 4 named query traversals.
    """

    def __init__(self):
        # project_id -> { "nodes": { node_id: { "labels": set(), "props": dict } }, "edges": list[dict] }
        self._projects: Dict[str, Dict[str, Any]] = {}

    def _get_project(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self._projects:
            self._projects[project_id] = {"nodes": {}, "edges": []}
        return self._projects[project_id]

    def purge_project(self, project_id: str) -> None:
        """Purge all nodes and relationships for a project (stale-data MVP policy)."""
        if project_id in self._projects:
            del self._projects[project_id]

    def upsert_node(self, project_id: str, node_id: str, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        proj = self._get_project(project_id)
        props = dict(properties)
        props["id"] = node_id
        props["project_id"] = project_id
        if node_id in proj["nodes"]:
            proj["nodes"][node_id]["labels"].add(label)
            proj["nodes"][node_id]["props"].update(props)
        else:
            proj["nodes"][node_id] = {
                "id": node_id,
                "labels": {label},
                "props": props,
            }
        return proj["nodes"][node_id]

    def upsert_edge(
        self,
        project_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        proj = self._get_project(project_id)
        props = properties or {}
        # Avoid duplicate edges (idempotency)
        for edge in proj["edges"]:
            if edge["source"] == source_id and edge["target"] == target_id and edge["relationship"] == rel_type:
                edge["properties"].update(props)
                return edge

        new_edge = {
            "source": source_id,
            "target": target_id,
            "relationship": rel_type,
            "properties": props,
        }
        proj["edges"].append(new_edge)
        return new_edge

    def get_topology(self, project_id: str) -> Dict[str, Any]:
        proj = self._get_project(project_id)
        nodes = []
        for n_id, n_data in proj["nodes"].items():
            label = list(n_data["labels"])[0] if n_data["labels"] else "Node"
            nodes.append({
                "id": n_id,
                "label": n_data["props"].get("name") or n_data["props"].get("identifier") or n_data["props"].get("path") or n_id,
                "entity_type": label,
                "properties": n_data["props"],
            })
        return {
            "project_id": project_id,
            "nodes": nodes,
            "edges": list(proj["edges"]),
        }

    def query_untested_requirements(self, project_id: str) -> List[Dict[str, Any]]:
        proj = self._get_project(project_id)
        # Find all Requirement nodes
        req_nodes = [
            n for n in proj["nodes"].values()
            if "Requirement" in n["labels"]
        ]
        results = []
        for req in req_nodes:
            req_id = req["id"]
            # Check if tested by any test
            has_test = any(
                e["source"] == req_id and e["relationship"] == "TESTED_BY"
                for e in proj["edges"]
            )
            if not has_test:
                # Find implemented_by functions
                linked_fns = []
                for e in proj["edges"]:
                    if e["source"] == req_id and e["relationship"] == "IMPLEMENTED_BY":
                        target_fn = proj["nodes"].get(e["target"])
                        if target_fn:
                            fn_name = target_fn["props"].get("qualified_name") or target_fn["props"].get("name") or target_fn["id"]
                            linked_fns.append(fn_name)
                results.append({
                    "requirement_id": req_id,
                    "identifier": req["props"].get("identifier", "REQ-UNKNOWN"),
                    "title": req["props"].get("title", ""),
                    "description": req["props"].get("description", ""),
                    "priority": req["props"].get("priority", "MEDIUM"),
                    "status": req["props"].get("status", "DRAFT"),
                    "linked_functions": linked_fns,
                })
        return results

    def query_failure_related_functions(self, project_id: str, failure_id: Optional[str] = None) -> List[Dict[str, Any]]:
        proj = self._get_project(project_id)
        failure_nodes = [
            n for n in proj["nodes"].values()
            if "Failure" in n["labels"] and (failure_id is None or n["id"] == failure_id)
        ]
        results = []
        for f in failure_nodes:
            f_id = f["id"]
            # Find execution
            exec_id = None
            for e in proj["edges"]:
                if e["target"] == f_id and e["relationship"] == "PRODUCED":
                    exec_id = e["source"]
                    break
            # Find related functions
            related_fns = []
            for e in proj["edges"]:
                if e["source"] == f_id and e["relationship"] == "RELATED_TO":
                    fn_node = proj["nodes"].get(e["target"])
                    if fn_node:
                        related_fns.append({
                            "id": fn_node["id"],
                            "name": fn_node["props"].get("name", ""),
                            "qualified_name": fn_node["props"].get("qualified_name", ""),
                            "file_path": fn_node["props"].get("file_path", ""),
                        })
            results.append({
                "failure_id": f_id,
                "failure_title": f["props"].get("title", ""),
                "error_message": f["props"].get("error_message", ""),
                "execution_id": exec_id,
                "related_functions": related_fns,
            })
        return results

    def query_commit_impact(self, project_id: str, commit_hash: Optional[str] = None) -> List[Dict[str, Any]]:
        proj = self._get_project(project_id)
        commits = [
            n for n in proj["nodes"].values()
            if "Commit" in n["labels"] and (commit_hash is None or n["props"].get("commit_hash") == commit_hash or n["id"] == commit_hash)
        ]
        results = []
        for c in commits:
            c_id = c["id"]
            c_hash = c["props"].get("commit_hash", c_id)
            # Files modified
            modified_files = []
            file_ids = []
            for e in proj["edges"]:
                if e["source"] == c_id and e["relationship"] == "MODIFIES":
                    file_node = proj["nodes"].get(e["target"])
                    if file_node:
                        modified_files.append(file_node["props"].get("path", file_node["id"]))
                        file_ids.append(file_node["id"])
            # Impacted functions in those files
            impacted_fns = []
            fn_ids = []
            for e in proj["edges"]:
                if e["source"] in file_ids and e["relationship"] == "CONTAINS":
                    fn_node = proj["nodes"].get(e["target"])
                    if fn_node and "Function" in fn_node["labels"]:
                        fn_name = fn_node["props"].get("qualified_name") or fn_node["props"].get("name")
                        impacted_fns.append(fn_name)
                        fn_ids.append(fn_node["id"])
            # Dependent tests linked to requirements implementing those functions
            dependent_tests = []
            for fn_id in fn_ids:
                for e1 in proj["edges"]:
                    if e1["target"] == fn_id and e1["relationship"] == "IMPLEMENTED_BY":
                        req_id = e1["source"]
                        for e2 in proj["edges"]:
                            if e2["source"] == req_id and e2["relationship"] == "TESTED_BY":
                                test_node = proj["nodes"].get(e2["target"])
                                if test_node:
                                    dependent_tests.append(test_node["props"].get("name", test_node["id"]))

            results.append({
                "commit_hash": c_hash,
                "modified_files": list(set(modified_files)),
                "impacted_functions": list(set(impacted_fns)),
                "dependent_tests": list(set(dependent_tests)),
            })
        return results

    def query_call_neighborhood(self, project_id: str, function_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        proj = self._get_project(project_id)
        # Match target function by name, qualified_name, suffix, or id
        target_fns = []
        for n in proj["nodes"].values():
            if "Function" in n["labels"]:
                name = n["props"].get("name", "")
                qname = n["props"].get("qualified_name", "")
                nid = n["id"]
                if (
                    name == function_name
                    or qname == function_name
                    or nid == function_name
                    or (function_name and (name in function_name or qname.endswith("." + function_name) or function_name.endswith("." + name)))
                ):
                    target_fns.append(n)
        results = []
        for target in target_fns:
            t_id = target["id"]
            callers = []
            callees = []
            for e in proj["edges"]:
                if e["target"] == t_id and e["relationship"] == "CALLS":
                    caller_node = proj["nodes"].get(e["source"])
                    if caller_node:
                        callers.append(caller_node["props"].get("qualified_name") or caller_node["props"].get("name"))
                if e["source"] == t_id and e["relationship"] == "CALLS":
                    callee_node = proj["nodes"].get(e["target"])
                    if callee_node:
                        callees.append(callee_node["props"].get("qualified_name") or callee_node["props"].get("name"))

            results.append({
                "target_function": target["props"].get("name", function_name),
                "callers": list(set(callers)),
                "callees": list(set(callees)),
                "depth": depth,
            })
        return results


class Neo4jClient:
    """Async Neo4j Client wrapper with fallback support."""

    def __init__(self):
        self._driver: Optional[Any] = None
        self._in_memory = InMemoryGraphStore()
        self._use_in_memory = True

    async def initialize(self) -> None:
        """Attempt connection to real Neo4j server; fallback to in-memory store if unavailable."""
        if NEO4J_AVAILABLE and settings.NEO4J_URI:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                # Verify connectivity
                await self._driver.verify_connectivity()
                self._use_in_memory = False
                logger.info(f"Connected to Neo4j Knowledge Graph at {settings.NEO4J_URI}")
            except Exception as e:
                logger.warning(f"Neo4j connection failed ({e}). Using in-memory graph fallback.")
                self._use_in_memory = True
        else:
            self._use_in_memory = True

    @property
    def in_memory_store(self) -> InMemoryGraphStore:
        return self._in_memory

    @property
    def is_in_memory(self) -> bool:
        return self._use_in_memory

    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query against Neo4j or route to in-memory store."""
        if not self._use_in_memory and self._driver:
            try:
                async with self._driver.session() as session:
                    result = await session.run(query, parameters or {})
                    records = await result.data()
                    return records
            except Exception as e:
                logger.error(f"Error executing Neo4j Cypher query: {e}")
                raise
        return []

    async def close(self) -> None:
        """Close driver connections."""
        if self._driver:
            await self._driver.close()
            self._driver = None


# Global singleton instance
neo4j_client = Neo4jClient()
