"""
CodeSentinel Shared Schemas: CodeEntity Contract.

Defines schemas for parsed code structural entities (files, modules, classes, functions,
methods), syntax nodes, AST signatures, and relationship bindings.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class EntityType(str, Enum):
    """Categorization of code structural entities extracted via AST / Tree-sitter."""
    FILE = "FILE"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    INTERFACE = "INTERFACE"
    TYPE_ALIAS = "TYPE_ALIAS"
    VARIABLE = "VARIABLE"


class Visibility(str, Enum):
    """Access modifier / visibility level."""
    PUBLIC = "PUBLIC"
    PROTECTED = "PROTECTED"
    PRIVATE = "PRIVATE"
    INTERNAL = "INTERNAL"


class CodeLocation(BaseModel):
    """Exact source code position coordinates."""
    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(..., description="Relative path within the repository.")
    start_line: int = Field(..., ge=1, description="Start line index (1-based).")
    end_line: int = Field(..., ge=1, description="End line index (1-based).")
    start_column: int = Field(0, ge=0, description="Start column character offset.")
    end_column: int = Field(0, ge=0, description="End column character offset.")


class CodeParameter(BaseModel):
    """Typed signature parameter."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter identifier.")
    type_annotation: Optional[str] = Field(default=None, description="Type hint string.")
    default_value: Optional[str] = Field(default=None, description="String representation of default value.")
    is_required: bool = Field(default=True, description="Whether parameter is mandatory.")


class CodeEntityBase(BaseModel):
    """Base schema for CodeEntity."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    name: str = Field(
        ...,
        description="Symbol name (e.g. 'UserService', 'authenticate_user')."
    )
    qualified_name: str = Field(
        ...,
        description="Full canonical path (e.g. 'app.services.auth.UserService.authenticate_user')."
    )
    entity_type: EntityType = Field(
        ...,
        description="Type of structural entity."
    )
    language: str = Field(
        ...,
        description="Programming language identifier (e.g., 'python', 'typescript', 'go')."
    )
    location: CodeLocation = Field(
        ...,
        description="Source code file coordinates."
    )
    parent_entity_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of containing class, module, or file entity."
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Extracted docstring or documentation comments."
    )
    source_code: Optional[str] = Field(
        default=None,
        description="Exact raw source code text of this entity."
    )
    parameters: List[CodeParameter] = Field(
        default_factory=list,
        description="List of parameters if entity is callable (function/method)."
    )
    return_type: Optional[str] = Field(
        default=None,
        description="Return type annotation string if applicable."
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        description="Symbol visibility modifier."
    )
    complexity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Cyclomatic / cognitive complexity score."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Imports or external symbol references required by this entity."
    )


class CodeEntityCreate(CodeEntityBase):
    """Creation payload for parsed code entity."""
    pass


class CodeEntityUpdate(BaseModel):
    """Update payload for modifying code entity metadata."""
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None)
    docstring: Optional[str] = Field(default=None)
    complexity_score: Optional[float] = Field(default=None)
    visibility: Optional[Visibility] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class CodeEntity(CodeEntityBase, BaseEntity):
    """
    CodeEntity domain entity contract.

    Serves as the structural atom for AST profiling, knowledge graph nodes,
    vector embeddings, and test generation targets.
    """
    ast_hash: Optional[str] = Field(
        default=None,
        description="Cryptographic hash of the normalized AST subtree for change detection."
    )
    embedding_id: Optional[str] = Field(
        default=None,
        description="Vector point ID in Qdrant storage."
    )
