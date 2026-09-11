"""
CodeSentinel RAG Module: Service Layer.

Orchestrates:
1. Embedding and indexing project code, requirements, tests, findings, and documentation into Qdrant.
2. Building hybrid RAG context (combining vector hits and Neo4j graph traversals).
"""

from typing import Any, Dict, List, Optional, Union
import uuid

from app.core.logging import logger
from app.knowledge_graph.service import KnowledgeGraphService
from app.rag.chunker import CodeChunker
from app.rag.client import qdrant_client
from app.rag.context_builder import RAGContextBuilder
from app.rag.embeddings import embedding_pipeline
from app.rag.models import (
    RAGChunk,
    RAGCollection,
    RAGContext,
    VectorSearchResult,
)


class RAGService:
    """Core RAG service for vector indexing and context retrieval."""

    @classmethod
    async def index_project_content(
        cls,
        project_id: Union[str, uuid.UUID],
        system_model_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts chunks from the project's Software System Model,
        generates dense vector embeddings, and stores them in Qdrant.
        """
        pid_str = str(project_id)
        logger.info(f"Indexing vector embeddings for project {pid_str} in Qdrant...")

        # 1. Fetch system model from Module 2 API unless provided
        system_model = system_model_override
        if not system_model:
            system_model = await KnowledgeGraphService.fetch_system_model(pid_str)

        # 2. Chunk system model into semantic pieces
        chunks = CodeChunker.chunk_system_model(pid_str, system_model)
        if not chunks:
            logger.info(f"No content chunks found to index for project {pid_str}.")
            return {
                "project_id": pid_str,
                "total_chunks_indexed": 0,
                "collections_updated": [],
            }

        # 3. Clear existing vectors for this project (stale-data full re-index strategy)
        if qdrant_client.is_in_memory:
            qdrant_client.in_memory_store.clear_project(pid_str)

        # 4. Group chunks by target collection
        chunks_by_collection: Dict[RAGCollection, List[RAGChunk]] = {}
        for chk in chunks:
            if chk.collection not in chunks_by_collection:
                chunks_by_collection[chk.collection] = []
            chunks_by_collection[chk.collection].append(chk)

        total_indexed = 0
        updated_collections = []

        for col, col_chunks in chunks_by_collection.items():
            texts = [c.content for c in col_chunks]
            embeddings = embedding_pipeline.embed_documents(texts)

            points = []
            for i, chk in enumerate(col_chunks):
                points.append({
                    "id": chk.chunk_id,
                    "vector": embeddings[i],
                    "payload": {
                        "project_id": pid_str,
                        "chunk_type": chk.chunk_type.value,
                        "title": chk.title,
                        "content": chk.content,
                        "file_path": chk.file_path,
                        "start_line": chk.start_line,
                        "end_line": chk.end_line,
                        "metadata": chk.metadata,
                    }
                })

            await qdrant_client.upsert_chunks(
                collection=col,
                project_id=pid_str,
                points=points
            )
            total_indexed += len(points)
            updated_collections.append(col.value)

        logger.info(f"Indexed {total_indexed} chunks across {len(updated_collections)} collections for project {pid_str}.")
        return {
            "project_id": pid_str,
            "total_chunks_indexed": total_indexed,
            "collections_updated": updated_collections,
        }

    @classmethod
    async def query_context(
        cls,
        project_id: Union[str, uuid.UUID],
        query: str,
        top_k: int = 5,
        target_collections: Optional[List[RAGCollection]] = None,
    ) -> RAGContext:
        """Assemble hybrid vector + graph context for a project query."""
        return await RAGContextBuilder.build_context(
            project_id=project_id,
            query=query,
            top_k=top_k,
            target_collections=target_collections,
        )
