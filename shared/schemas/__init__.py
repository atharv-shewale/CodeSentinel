"""
CodeSentinel Shared Schemas Package.

The single source of truth for all domain entities, contract payloads,
and envelope definitions across CodeSentinel. No module may import another
module's internal schemas directly.
"""

from .common import (
    APIError,
    APIResponse,
    BaseEntity,
    PaginationMeta,
    SortOrder,
    utc_now,
)
from .project import (
    Project,
    ProjectBase,
    ProjectCreate,
    ProjectStatus,
    ProjectUpdate,
    RepoProvider,
)
from .requirement import (
    Requirement,
    RequirementBase,
    RequirementCreate,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    RequirementUpdate,
)
from .code_entity import (
    CodeEntity,
    CodeEntityBase,
    CodeEntityCreate,
    CodeEntityUpdate,
    CodeLocation,
    CodeParameter,
    EntityType,
    Visibility,
)
from .api_route import (
    APIRoute,
    APIRouteBase,
    APIRouteCreate,
    APIRouteUpdate,
    AuthRequirement,
    HTTPMethod,
    ParameterLocation,
    RouteParameter,
)
from .test_case import (
    AssertionSpec,
    TestCase,
    TestCaseBase,
    TestCaseCreate,
    TestCaseUpdate,
    TestProvenance,
    TestStatus,
    TestType,
)
from .test_execution import (
    CoverageMetrics,
    ExecutionEnvironment,
    ExecutionStatus,
    TestExecution,
    TestExecutionBase,
    TestExecutionCreate,
    TestResultItem,
)
from .failure import (
    Failure,
    FailureBase,
    FailureCategory,
    FailureCreate,
    FailureSeverity,
    FailureStatus,
    FailureUpdate,
    RootCauseAnalysis,
)
from .audit import (
    AuditCategory,
    AuditFinding,
    AuditFindingBase,
    AuditFindingCreate,
    AuditFindingUpdate,
    AuditSeverity,
    AuditStatus,
    ComplianceStandard,
)
from .jobs import (
    JobProgress,
    JobState,
    JobStatus,
    JobType,
)

__all__ = [
    # Common / Envelopes
    "APIError",
    "APIResponse",
    "BaseEntity",
    "PaginationMeta",
    "SortOrder",
    "utc_now",
    # Project
    "Project",
    "ProjectBase",
    "ProjectCreate",
    "ProjectStatus",
    "ProjectUpdate",
    "RepoProvider",
    # Requirement
    "Requirement",
    "RequirementBase",
    "RequirementCreate",
    "RequirementPriority",
    "RequirementStatus",
    "RequirementType",
    "RequirementUpdate",
    # CodeEntity
    "CodeEntity",
    "CodeEntityBase",
    "CodeEntityCreate",
    "CodeEntityUpdate",
    "CodeLocation",
    "CodeParameter",
    "EntityType",
    "Visibility",
    # APIRoute
    "APIRoute",
    "APIRouteBase",
    "APIRouteCreate",
    "APIRouteUpdate",
    "AuthRequirement",
    "HTTPMethod",
    "ParameterLocation",
    "RouteParameter",
    # TestCase
    "AssertionSpec",
    "TestCase",
    "TestCaseBase",
    "TestCaseCreate",
    "TestCaseUpdate",
    "TestProvenance",
    "TestStatus",
    "TestType",
    # TestExecution
    "CoverageMetrics",
    "ExecutionEnvironment",
    "ExecutionStatus",
    "TestExecution",
    "TestExecutionBase",
    "TestExecutionCreate",
    "TestResultItem",
    # Failure
    "Failure",
    "FailureBase",
    "FailureCategory",
    "FailureCreate",
    "FailureSeverity",
    "FailureStatus",
    "FailureUpdate",
    "RootCauseAnalysis",
    # Audit
    "AuditCategory",
    "AuditFinding",
    "AuditFindingBase",
    "AuditFindingCreate",
    "AuditFindingUpdate",
    "AuditSeverity",
    "AuditStatus",
    "ComplianceStandard",
    # Jobs
    "JobProgress",
    "JobState",
    "JobStatus",
    "JobType",
]
