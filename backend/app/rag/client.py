"""
CodeSentinel RAG Module: Qdrant Vector Database Client.

Enforces:
1. Exact 6 contract collections (CONTRACTS.md).
2. Strict non-optional project_id filtering at the function signature level.
3. Zero cross-project leakage.
4. Seamless in-memory fallback vector store for unit tests.
"""

from typing import Any, Dict, List, Optional, Union
import uuid
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.rag.models import RAGCollection, VectorSearchResult

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None


class InMemoryVectorStore:
    """
    In-memory vector store simulator for offline development and test execution.
    Maintains isolated collections with strict project_id filtering to test tenant isolation.
    """

    def __init__(self):
        # collection_name -> list of { "id": str, "vector": list[float], "payload": dict }
        self._collections: Dict[str, List[Dict[str, Any]]] = {
            c.value: [] for c in RAGCollection
        }

    def clear(self) -> None:
        """Clear all stored vectors across all collections."""
        for c in self._collections:
            self._collections[c] = []

    def clear_project(self, project_id: str) -> None:
        """Clear vectors for a specific project."""
        for c in self._collections:
            self._collections[c] = [
                pt for pt in self._collections[c]
                if pt["payload"].get("project_id") != project_id
            ]

    def upsert(self, collection_name: str, points: List[Dict[str, Any]]) -> None:
        if collection_name not in self._collections:
            self._collections[collection_name] = []

        for pt in points:
            # Ensure project_id exists in payload
            if "project_id" not in pt["payload"]:
                raise ValueError("Point payload must contain 'project_id' for tenant isolation.")

            # Replace or add point
            self._collections[collection_name] = [
                p for p in self._collections[collection_name]
                if p["id"] != pt["id"]
            ]
            self._collections[collection_name].append(pt)

    def search(
        self,
        collection_name: str,
        project_id: str,  # Mandatory filter
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[VectorSearchResult]:
        """Search vector database enforcing strict project_id matching."""
        if collection_name not in self._collections:
            return []

        pts = self._collections[collection_name]
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)

        matches = []
        for pt in pts:
            # Enforce strict project_id match (zero cross-tenant leakage)
            if pt["payload"].get("project_id") != project_id:
                continue

            p_vec = np.array(pt["vector"], dtype=np.float32)
            p_norm = np.linalg.norm(p_vec)
            if q_norm > 0 and p_norm > 0:
                sim = float(np.dot(q_vec, p_vec) / (q_norm * p_norm))
            else:
                sim = 0.0

            matches.append((sim, pt))

        # Sort descending by cosine similarity
        matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = matches[:top_k]

        results = []
        for score, pt in top_matches:
            payload = pt["payload"]
            results.append(VectorSearchResult(
                point_id=pt["id"],
                project_id=project_id,
                collection=collection_name,
                chunk_type=payload.get("chunk_type", "UNKNOWN"),
                title=payload.get("title", ""),
                content=payload.get("content", ""),
                file_path=payload.get("file_path"),
                score=round(max(0.0, score), 4),
                metadata=payload.get("metadata", {}),
            ))

        return results


class QdrantVectorClient:
    """Async/Sync Qdrant client manager with strict tenant isolation."""

    VECTOR_SIZE = 384

    def __init__(self):
        self._client: Optional[Any] = None
        self._in_memory = InMemoryVectorStore()
        self._use_in_memory = True

    async def initialize(self) -> None:
        """Initialize connection to Qdrant or fallback to in-memory store."""
        if QDRANT_AVAILABLE and settings.QDRANT_HOST:
            try:
                self._client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=5.0,
                )
                # Verify and ensure all 6 collections exist
                for collection in RAGCollection:
                    if not self._client.collection_exists(collection.value):
                        self._client.create_collection(
                            collection_name=collection.value,
                            vectors_config=VectorParams(
                                size=self.VECTOR_SIZE,
                                distance=Distance.COSINE
                            )
                        )
                self._use_in_memory = False
                logger.info("Connected to Qdrant vector database.")
                return
            except Exception as e:
                logger.warning(f"Qdrant connection failed ({e}). Using in-memory vector store fallback.")

        self._use_in_memory = True

    @property
    def is_in_memory(self) -> bool:
        return self._use_in_memory

    @property
    def in_memory_store(self) -> InMemoryVectorStore:
        return self._in_memory

    async def upsert_chunks(
        self,
        collection: RAGCollection,
        project_id: Union[str, uuid.UUID],  # Mandatory tenant parameter
        points: List[Dict[str, Any]],
    ) -> None:
        """
        Upsert vector embeddings into Qdrant collection.
        Enforces project_id field in payload for strict multi-tenant filtering.
        """
        pid_str = str(project_id)
        # Ensure project_id is injected in every payload
        for pt in points:
            if "payload" not in pt:
                pt["payload"] = {}
            pt["payload"]["project_id"] = pid_str

        if self._use_in_memory or not self._client:
            self._in_memory.upsert(collection.value, points)
            return

        try:
            qdrant_points = [
                PointStruct(
                    id=pt["id"] if isinstance(pt["id"], (int, str)) else str(pt["id"]),
                    vector=pt["vector"],
                    payload=pt["payload"]
                )
                for pt in points
            ]
            self._client.upsert(
                collection_name=collection.value,
                points=qdrant_points,
                wait=True
            )
        except Exception as e:
            logger.error(f"Error upserting points to Qdrant collection {collection.value}: {e}")
            self._in_memory.upsert(collection.value, points)

    async def search_vectors(
        self,
        project_id: Union[str, uuid.UUID],  # MANDATORY: non-optional project_id filter
        collection: RAGCollection,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[VectorSearchResult]:
        """
        Search vector database for a single project.
        CRITICAL: Never performs un-filtered searches to prevent cross-tenant data leakage.
        """
        pid_str = str(project_id)

        if self._use_in_memory or not self._client:
            return self._in_memory.search(
                collection_name=collection.value,
                project_id=pid_str,
                query_vector=query_vector,
                top_k=top_k,
            )

        try:
            # Enforce Qdrant payload filter for project_id
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="project_id",
                        match=MatchValue(value=pid_str)
                    )
                ]
            )

            hits = self._client.search(
                collection_name=collection.value,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=top_k,
            )

            results = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(VectorSearchResult(
                    point_id=str(hit.id),
                    project_id=pid_str,
                    collection=collection.value,
                    chunk_type=payload.get("chunk_type", "UNKNOWN"),
                    title=payload.get("title", ""),
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path"),
                    score=round(float(hit.score), 4),
                    metadata=payload.get("metadata", {}),
                ))
            return results

        except Exception as e:
            logger.error(f"Qdrant search error ({e}). Falling back to in-memory search.")
            return self._in_memory.search(
                collection_name=collection.value,
                project_id=pid_str,
                query_vector=query_vector,
                top_k=top_k,
            )


# Global singleton instance
qdrant_client = QdrantVectorClient()
