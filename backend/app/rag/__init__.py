"""
CodeSentinel RAG Package.

Provides dense embeddings, semantic chunking, Qdrant multi-collection indexing,
and hybrid vector + graph context building.
"""

from .models import (
    ChunkType,
    RAGChunk,
    RAGCollection,
    RAGContext,
    RAGSearchRequest,
    VectorSearchResult,
)
from .embeddings import EmbeddingPipeline, embedding_pipeline
from .chunker import CodeChunker
from .client import QdrantVectorClient, qdrant_client
from .context_builder import RAGContextBuilder
from .service import RAGService

__all__ = [
    "ChunkType",
    "CodeChunker",
    "EmbeddingPipeline",
    "QdrantVectorClient",
    "RAGChunk",
    "RAGCollection",
    "RAGContext",
    "RAGContextBuilder",
    "RAGSearchRequest",
    "RAGService",
    "VectorSearchResult",
    "embedding_pipeline",
    "qdrant_client",
]
