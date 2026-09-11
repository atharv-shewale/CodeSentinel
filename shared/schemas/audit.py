"""
CodeSentinel Shared Schemas: AuditFinding & Compliance Contract.

Defines schemas for static analysis findings, security vulnerabilities,
anti-patterns, compliance checks, and architectural governance violations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid
from .common import BaseEntity
from .code_entity import CodeLocation


class AuditSeverity(str, Enum):
    """Severity classification of audit findings."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AuditCategory(str, Enum):
    """Categorization of audit rules."""
    SECURITY_VULNERABILITY = "SECURITY_VULNERABILITY"
    CODE_SMELL = "CODE_SMELL"
    PERFORMANCE_HOTSPOT = "PERFORMANCE_HOTSPOT"
    API_CONTRACT_VIOLATION = "API_CONTRACT_VIOLATION"
    ARCHITECTURE_DRIFT = "ARCHITECTURE_DRIFT"
    TYPE_SAFETY = "TYPE_SAFETY"
    DOCUMENTATION_DEFICIT = "DOCUMENTATION_DEFICIT"
    COMPLIANCE_NON_CONFORMANCE = "COMPLIANCE_NON_CONFORMANCE"


class ComplianceStandard(str, Enum):
    """Governing standards / frameworks."""
    OWASP_TOP_10 = "OWASP_TOP_10"
    CWE = "CWE"
    SANS_TOP_25 = "SANS_TOP_25"
    PCI_DSS = "PCI_DSS"
    HIPAA = "HIPAA"
    SOC2 = "SOC2"
    CUSTOM_ORGANIZATION = "CUSTOM_ORGANIZATION"


class AuditStatus(str, Enum):
    """Lifecycle status of an audit finding."""
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    SUPPRESSED = "SUPPRESSED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FIX_IN_PROGRESS = "FIX_IN_PROGRESS"
    RESOLVED = "RESOLVED"


class AuditFindingBase(BaseModel):
    """Base schema for AuditFinding."""
    model_config = ConfigDict(extra="forbid")

    project_id: uuid.UUID = Field(
        ...,
        description="Associated project identifier."
    )
    rule_id: str = Field(
        ...,
        description="Static analyzer or compliance rule identifier (e.g., 'SEC-004', 'AST-COMPLEXITY-10')."
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Concise description of the finding."
    )
    description: str = Field(
        ...,
        description="Comprehensive technical explanation and security/architectural impact."
    )
    category: AuditCategory = Field(
        default=AuditCategory.CODE_SMELL,
        description="Categorization of finding."
    )
    severity: AuditSeverity = Field(
        default=AuditSeverity.MEDIUM,
        description="Severity rating."
    )
    standard: Optional[ComplianceStandard] = Field(
        default=None,
        description="Referenced compliance framework standard if applicable."
    )
    standard_reference_id: Optional[str] = Field(
        default=None,
        description="Standard reference identifier (e.g. 'CWE-89', 'A03:2021-Injection')."
    )
    target_entity_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of associated CodeEntity."
    )
    location: CodeLocation = Field(
        ...,
        description="File path and coordinate location of defect."
    )
    remediation_suggestion: Optional[str] = Field(
        default=None,
        description="Recommended code refactoring, fix diff, or mitigation strategy."
    )
    detected_by: List[str] = Field(
        default_factory=lambda: ["codesentinel-static-analyzer"],
        description="List of tools or detectors that identified or confirmed this finding (e.g. ['semgrep', 'codesentinel-secrets-detector'])."
    )


class AuditFindingCreate(AuditFindingBase):
    """Payload to log a new audit finding."""
    pass


class AuditFindingUpdate(BaseModel):
    """Payload to update finding status or triage details."""
    model_config = ConfigDict(extra="forbid")

    status: Optional[AuditStatus] = Field(default=None)
    severity: Optional[AuditSeverity] = Field(default=None)
    remediation_suggestion: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class AuditFinding(AuditFindingBase, BaseEntity):
    """
    AuditFinding domain entity contract.

    Stores discrete security, architectural, and quality defects discovered across AST,
    dependency graphs, and static analyzers.
    """
    status: AuditStatus = Field(
        default=AuditStatus.OPEN,
        description="Current audit triage and remediation status."
    )
    cvss_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="CVSS score (0.0 to 10.0) for security vulnerabilities."
    )
