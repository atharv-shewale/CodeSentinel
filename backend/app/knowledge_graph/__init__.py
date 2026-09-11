"""
CodeSentinel Knowledge Graph Package.

Provides Neo4j graph materialization, idempotent loading, and named traversals.
"""

from .models import (
    CallNeighborhoodItem,
    CommitImpactItem,
    FailureFunctionItem,
    GraphEdge,
    GraphNode,
    GraphNodeType,
    GraphRelationshipType,
    GraphResponse,
    GraphTopologyResponse,
    KnowledgeQueryType,
    UntestedRequirementItem,
)
from .service import KnowledgeGraphService
from .client import neo4j_client

__all__ = [
    "CallNeighborhoodItem",
    "CommitImpactItem",
    "FailureFunctionItem",
    "GraphEdge",
    "GraphNode",
    "GraphNodeType",
    "GraphRelationshipType",
    "GraphResponse",
    "GraphTopologyResponse",
    "KnowledgeGraphService",
    "KnowledgeQueryType",
    "UntestedRequirementItem",
    "neo4j_client",
]
