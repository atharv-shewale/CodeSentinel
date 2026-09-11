"""
CodeSentinel RAG Module: Hybrid Vector + Graph Context Builder.

Combines semantic dense vector search results across the 6 collections with
relational Neo4j Knowledge Graph traversals (call graph neighborhood, untested requirements,
failure paths) to produce a rich, evidence-grounded RAGContext object.
"""

from typing import Any, Dict, List, Optional, Set, Union
import uuid

from app.knowledge_graph.models import KnowledgeQueryType
from app.knowledge_graph.service import KnowledgeGraphService
from app.rag.client import qdrant_client
from app.rag.embeddings import embedding_pipeline
from app.rag.models import (
    RAGCollection,
    RAGContext,
    VectorSearchResult,
)


class RAGContextBuilder:
    """Assembles unified RAG context combining dense vector hits with graph traversals."""

    @classmethod
    async def build_context(
        cls,
        project_id: Union[str, uuid.UUID],
        query: str,
        top_k: int = 5,
        target_collections: Optional[List[RAGCollection]] = None,
    ) -> RAGContext:
        """
        Executes hybrid RAG context assembly:
        1. Embeds the natural language query via EmbeddingPipeline.
        2. Queries Qdrant vector collections with mandatory project_id filter.
        3. Identifies key code symbols and traverses Neo4j graph for callers, callees, and linked specs.
        4. Extracts concrete evidence citations (file paths, function names, requirement IDs).
        """
        pid_str = str(project_id)
        query_vector = embedding_pipeline.embed_query(query)

        collections_to_search = target_collections or [
            RAGCollection.PROJECT_CODE,
            RAGCollection.PROJECT_REQUIREMENTS,
            RAGCollection.PROJECT_TESTS,
            RAGCollection.PROJECT_DOCUMENTATION,
            RAGCollection.PROJECT_FINDINGS,
            RAGCollection.PROJECT_LOGS,
        ]

        code_results: List[VectorSearchResult] = []
        req_results: List[VectorSearchResult] = []
        test_results: List[VectorSearchResult] = []
        doc_results: List[VectorSearchResult] = []
        finding_results: List[VectorSearchResult] = []
        log_results: List[VectorSearchResult] = []

        # 1. Execute vector searches across target collections
        for col in collections_to_search:
            hits = await qdrant_client.search_vectors(
                project_id=pid_str,
                collection=col,
                query_vector=query_vector,
                top_k=top_k,
            )
            if col == RAGCollection.PROJECT_CODE:
                code_results.extend(hits)
            elif col == RAGCollection.PROJECT_REQUIREMENTS:
                req_results.extend(hits)
            elif col == RAGCollection.PROJECT_TESTS:
                test_results.extend(hits)
            elif col == RAGCollection.PROJECT_DOCUMENTATION:
                doc_results.extend(hits)
            elif col == RAGCollection.PROJECT_FINDINGS:
                finding_results.extend(hits)
            elif col == RAGCollection.PROJECT_LOGS:
                log_results.extend(hits)

        # 2. Extract discovered entity symbols for graph neighborhood traversal
        discovered_symbols: Set[str] = set()
        citations: Set[str] = set()

        for hit in code_results:
            if hit.file_path:
                citations.add(hit.file_path)
            name = hit.metadata.get("name")
            qname = hit.metadata.get("qualified_name")
            if name:
                discovered_symbols.add(name)
                citations.add(name)
            if qname:
                discovered_symbols.add(qname)
                citations.add(qname)

        # Also extract identifier tokens from the query itself
        for token in query.replace("?", " ").replace("(", " ").replace(")", " ").replace(",", " ").split():
            clean_tok = token.strip()
            if len(clean_tok) >= 3 and ("_" in clean_tok or clean_tok.startswith("REQ-")):
                discovered_symbols.add(clean_tok)

        for hit in req_results:
            ident = hit.metadata.get("identifier")
            if ident:
                citations.add(ident)

        for hit in test_results:
            if hit.file_path:
                citations.add(hit.file_path)
            tname = hit.metadata.get("name")
            if tname:
                citations.add(tname)

        for hit in finding_results:
            if hit.file_path:
                citations.add(hit.file_path)
            rule = hit.metadata.get("rule_id")
            if rule:
                citations.add(rule)

        # 3. Perform Graph Traversals for discovered symbols
        graph_context: Dict[str, Any] = {
            "call_neighborhoods": [],
            "untested_requirements": [],
            "failure_traces": [],
        }

        # Graph traversal: Call graph neighborhood for discovered code symbols (prioritize symbols in query)
        seen_targets = set()
        ordered_symbols = sorted(
            discovered_symbols,
            key=lambda s: (0 if s.lower() in query.lower() else 1, s)
        )
        for symbol in ordered_symbols[:10]:
            try:
                neighborhood = await KnowledgeGraphService.get_call_neighborhood(
                    project_id=pid_str,
                    function_name=symbol,
                    depth=1,
                )
                if neighborhood:
                    for n in neighborhood:
                        if n.target_function not in seen_targets:
                            seen_targets.add(n.target_function)
                            graph_context["call_neighborhoods"].append(n.model_dump(mode="json"))
                            for caller in n.callers:
                                citations.add(caller)
                            for callee in n.callees:
                                citations.add(callee)
            except Exception:
                pass

        # Graph traversal: If query mentions 'test', 'requirement', or 'coverage', include untested requirements
        if any(term in query.lower() for term in ["test", "coverage", "untested", "requirement", "verify"]):
            try:
                untested = await KnowledgeGraphService.get_untested_requirements(project_id=pid_str)
                if untested:
                    graph_context["untested_requirements"] = [u.model_dump(mode="json") for u in untested]
                    for u in untested:
                        citations.add(u.identifier)
            except Exception:
                pass

        # Graph traversal: If query mentions 'failure', 'error', 'bug', 'crash', pull failure graphs
        if any(term in query.lower() for term in ["fail", "error", "bug", "crash", "exception", "rca"]):
            try:
                failures = await KnowledgeGraphService.get_failure_related_functions(project_id=pid_str)
                if failures:
                    graph_context["failure_traces"] = [f.model_dump(mode="json") for f in failures]
                    for f in failures:
                        citations.add(f.failure_id)
            except Exception:
                pass

        total_hits = (
            len(code_results)
            + len(req_results)
            + len(test_results)
            + len(doc_results)
            + len(finding_results)
            + len(log_results)
        )

        return RAGContext(
            project_id=pid_str,
            query=query,
            code_results=code_results,
            requirement_results=req_results,
            test_results=test_results,
            documentation_results=doc_results,
            finding_results=finding_results,
            log_results=log_results,
            graph_context=graph_context,
            evidence_citations=sorted(list(citations)),
            total_hits=total_hits,
        )
