"""
CodeSentinel RAG Module: Models and Schemas.

Defines schemas for vector collections, chunk payloads, search results, and assembled RAG context.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class RAGCollection(str, Enum):
    """The 6 Contract Vector Collections defined in CONTRACTS.md."""
    PROJECT_REQUIREMENTS = "project_requirements"
    PROJECT_CODE = "project_code"
    PROJECT_TESTS = "project_tests"
    PROJECT_DOCUMENTATION = "project_documentation"
    PROJECT_LOGS = "project_logs"
    PROJECT_FINDINGS = "project_findings"


class ChunkType(str, Enum):
    FUNCTION = "FUNCTION"
    CLASS = "CLASS"
    FILE = "FILE"
    REQUIREMENT = "REQUIREMENT"
    TEST = "TEST"
    DOCUMENTATION = "DOCUMENTATION"
    LOG = "LOG"
    FINDING = "FINDING"


class RAGChunk(BaseModel):
    """Normalized content chunk ready for vector embedding and upsert."""
    chunk_id: str
    project_id: str  # Mandatory tenant isolation key
    collection: RAGCollection
    chunk_type: ChunkType
    title: str
    content: str
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    """Individual vector retrieval hit."""
    point_id: str
    project_id: str
    collection: str
    chunk_type: str
    title: str
    content: str
    file_path: Optional[str] = None
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGSearchRequest(BaseModel):
    project_id: uuid.UUID = Field(..., description="Project UUID (mandatory filter).")
    query: str = Field(..., description="Semantic search query.")
    top_k: int = Field(default=5, ge=1, le=50, description="Max results.")
    collections: Optional[List[RAGCollection]] = Field(default=None, description="Collections to search.")


class RAGContext(BaseModel):
    """
    Unified RAG Context Object combining vector search hits across the 6 collections
    with structural Neo4j Knowledge Graph traversals (callers/callees/linked tests).
    """
    project_id: str
    query: str
    code_results: List[VectorSearchResult] = Field(default_factory=list)
    requirement_results: List[VectorSearchResult] = Field(default_factory=list)
    test_results: List[VectorSearchResult] = Field(default_factory=list)
    documentation_results: List[VectorSearchResult] = Field(default_factory=list)
    finding_results: List[VectorSearchResult] = Field(default_factory=list)
    log_results: List[VectorSearchResult] = Field(default_factory=list)
    graph_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph traversals: call graph neighbors, untested requirements, failure traces."
    )
    evidence_citations: List[str] = Field(
        default_factory=list,
        description="Verifiable citations (file paths, function qualified names, requirement IDs) found in context."
    )
    total_hits: int = 0
