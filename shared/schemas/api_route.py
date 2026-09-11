"""
CodeSentinel Shared Schemas: APIRoute Contract.

Defines schemas for discovered and analyzed HTTP endpoints, REST interfaces,
request/response schemas, parameter definitions, and auth requirements.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity


class HTTPMethod(str, Enum):
    """Standard HTTP request methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class AuthRequirement(str, Enum):
    """Authentication and authorization expectations."""
    NONE = "NONE"
    BEARER_TOKEN = "BEARER_TOKEN"
    API_KEY = "API_KEY"
    OAUTH2 = "OAUTH2"
    BASIC = "BASIC"
    CUSTOM = "CUSTOM"


class ParameterLocation(str, Enum):
    """Location of an HTTP parameter."""
    PATH = "PATH"
    QUERY = "QUERY"
    HEADER = "HEADER"
    COOKIE = "COOKIE"
    BODY = "BODY"


class RouteParameter(BaseModel):
    """Specification of an HTTP route parameter."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Parameter name.")
    location: ParameterLocation = Field(..., description="Parameter target location in HTTP request.")
    data_type: str = Field(..., description="Expected data type (e.g. 'string', 'integer', 'object').")
    required: bool = Field(default=True, description="Whether parameter is mandatory.")
    description: Optional[str] = Field(default=None, description="Human description of parameter.")
    schema_definition: Optional[Dict[str, Any]] = Field(default=None, description="JSON Schema object if complex type.")


class APIRouteBase(BaseModel):
    """Base schema for APIRoute."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    code_entity_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the handler function/controller CodeEntity."
    )
    path: str = Field(
        ...,
        description="URL pattern path (e.g. '/api/v1/users/{user_id}')."
    )
    http_method: HTTPMethod = Field(
        ...,
        description="HTTP method verb."
    )
    summary: Optional[str] = Field(
        default=None,
        description="Brief summary of endpoint functionality."
    )
    description: Optional[str] = Field(
        default=None,
        description="Full markdown description or endpoint specification."
    )
    auth_requirement: AuthRequirement = Field(
        default=AuthRequirement.NONE,
        description="Authentication mechanism."
    )
    parameters: List[RouteParameter] = Field(
        default_factory=list,
        description="Route path, query, header, or body parameter definitions."
    )
    request_body_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for expected request payload."
    )
    response_schemas: Dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of HTTP status codes (e.g., '200', '400') to JSON schema definitions."
    )
    tags: List[str] = Field(
        default_factory=list,
        description="OpenAPI tags / groupings."
    )


class APIRouteCreate(APIRouteBase):
    """Payload to record a newly discovered API route."""
    pass


class APIRouteUpdate(BaseModel):
    """Payload for partial updates to an API route."""
    model_config = ConfigDict(extra="forbid")

    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    auth_requirement: Optional[AuthRequirement] = Field(default=None)
    parameters: Optional[List[RouteParameter]] = Field(default=None)
    request_body_schema: Optional[Dict[str, Any]] = Field(default=None)
    response_schemas: Optional[Dict[str, Any]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class APIRoute(APIRouteBase, BaseEntity):
    """
    APIRoute domain entity contract.

    Represents inferred or discovered web service endpoints. Serves as targets for
    automated contract test generation and fuzzing.
    """
    is_deprecated: bool = Field(
        default=False,
        description="Whether this route is marked as deprecated."
    )
    version: Optional[str] = Field(
        default="v1",
        description="API version prefix or identifier."
    )
