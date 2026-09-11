"""
CodeSentinel Knowledge Graph Module: Models and Query Definitions.

Defines schemas for graph nodes, edges, query parameters, named traversal results,
and project topology responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class GraphNodeType(str, Enum):
    """Supported Knowledge Graph Node Types per CONTRACTS.md."""
    PROJECT = "Project"
    REQUIREMENT = "Requirement"
    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    API = "API"
    TEST = "Test"
    EXECUTION = "Execution"
    FAILURE = "Failure"
    FINDING = "Finding"
    COMMIT = "Commit"


class GraphRelationshipType(str, Enum):
    """Supported Knowledge Graph Relationship Types per CONTRACTS.md."""
    PROJECT_CONTAINS_FILE = "CONTAINS"
    FILE_CONTAINS_FUNCTION = "CONTAINS"
    FUNCTION_CALLS_FUNCTION = "CALLS"
    REQUIREMENT_IMPLEMENTED_BY_FUNCTION = "IMPLEMENTED_BY"
    REQUIREMENT_TESTED_BY_TEST = "TESTED_BY"
    TEST_EXECUTED_AS_EXECUTION = "EXECUTED_AS"
    EXECUTION_PRODUCED_FAILURE = "PRODUCED"
    FAILURE_RELATED_TO_FUNCTION = "RELATED_TO"
    COMMIT_MODIFIES_FILE = "MODIFIES"


class KnowledgeQueryType(str, Enum):
    """Named query types supported by GET /api/v1/knowledge/{project_id}/query."""
    UNTESTED_REQUIREMENTS = "untested_requirements"
    FAILURE_FUNCTIONS = "failure_functions"
    COMMIT_IMPACT = "commit_impact"
    CALL_NEIGHBORHOOD = "call_neighborhood"


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphTopologyResponse(BaseModel):
    project_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0


# Alias for compatibility with CONTRACTS.md catalog
GraphResponse = GraphTopologyResponse


class UntestedRequirementItem(BaseModel):
    requirement_id: str
    identifier: str
    title: str
    description: str
    priority: str
    status: str
    linked_functions: List[str] = Field(default_factory=list)


class FailureFunctionItem(BaseModel):
    failure_id: str
    failure_title: str
    error_message: str
    related_functions: List[Dict[str, Any]] = Field(default_factory=list)
    execution_id: Optional[str] = None


class CommitImpactItem(BaseModel):
    commit_hash: str
    modified_files: List[str] = Field(default_factory=list)
    impacted_functions: List[str] = Field(default_factory=list)
    dependent_tests: List[str] = Field(default_factory=list)


class CallNeighborhoodItem(BaseModel):
    target_function: str
    callers: List[str] = Field(default_factory=list)
    callees: List[str] = Field(default_factory=list)
    depth: int = 1
