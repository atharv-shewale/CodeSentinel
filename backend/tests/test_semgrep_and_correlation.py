"""
CodeSentinel Audits Module Tests: Real SAST (Semgrep) & Multi-Scanner Correlation.

Validates:
1. Semgrep integration detects eval() and unparameterized SQL, mapping cleanly to AuditFinding.
2. Deduplication engine merges findings on same file + overlapping line into ONE finding.
3. Merged finding carries combined detected_by list (e.g. ["codesentinel-secrets-detector", "semgrep"]).
4. Non-overlapping findings remain distinct.
5. Dependency scanner audits packages with pip-audit or verified fallback.
"""

import uuid
import pytest

from app.audits.correlation import FindingCorrelator, finding_correlator
from app.audits.dependency_scanner import DependencyVulnerabilityScanner, dependency_scanner
from app.audits.engine import AuditEngine
from app.audits.semgrep_scanner import SemgrepScanner, semgrep_scanner
from shared.schemas.audit import (
    AuditCategory,
    AuditFinding,
    AuditSeverity,
    AuditStatus,
    ComplianceStandard,
)
from shared.schemas.code_entity import CodeLocation


def test_semgrep_scanner_detects_eval_injection():
    """Verify SemgrepScanner detects dynamic eval() calls and maps to AuditFinding."""
    scanner = SemgrepScanner()
    if not scanner.is_available():
        pytest.skip("Semgrep binary not installed on runner")

    project_id = uuid.uuid4()
    source_code = (
        "# Secure math utilities\n"
        "def compute_user_expression(user_input: str):\n"
        "    result = eval(user_input)\n"
        "    return result\n"
    )

    findings = scanner.scan_source(
        project_id=project_id,
        file_path="app/calculator.py",
        source_code=source_code,
    )

    assert len(findings) >= 1, "Semgrep should detect eval injection"
    eval_finding = next((f for f in findings if "eval" in f.rule_id.lower() or "eval" in f.description.lower()), findings[0])

    assert eval_finding.category == AuditCategory.SECURITY_VULNERABILITY
    assert eval_finding.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
    assert eval_finding.detected_by == ["semgrep"]
    assert eval_finding.location.file_path == "app/calculator.py"
    assert eval_finding.location.start_line == 3
    assert "CWE-95" in (eval_finding.standard_reference_id or "") or eval_finding.standard == ComplianceStandard.CWE


def test_semgrep_scanner_detects_sql_injection():
    """Verify SemgrepScanner detects unparameterized SQL execution."""
    scanner = SemgrepScanner()
    if not scanner.is_available():
        pytest.skip("Semgrep binary not installed on runner")

    project_id = uuid.uuid4()
    source_code = (
        "import sqlite3\n"
        "def get_account(cursor, user_id: str):\n"
        "    cursor.execute(f'SELECT * FROM accounts WHERE id = {user_id}')\n"
        "    return cursor.fetchone()\n"
    )

    findings = scanner.scan_source(
        project_id=project_id,
        file_path="app/db/queries.py",
        source_code=source_code,
    )

    assert len(findings) >= 1, "Semgrep should detect unparameterized SQL injection"
    sql_finding = findings[0]
    assert sql_finding.category == AuditCategory.SECURITY_VULNERABILITY
    assert sql_finding.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
    assert "semgrep" in sql_finding.detected_by
    assert sql_finding.location.start_line == 3


def test_multi_scanner_deduplication_same_line_secret():
    """
    RATIONALE TEST:
    A fixture file has a hardcoded credential on line 2.
    Both Semgrep and CodeSentinel's regex secrets detector independently flag that line.
    Assert that AuditEngine.audit_security merges them into ONE finding with:
    detected_by=["codesentinel-secrets-detector", "semgrep"].
    """
    project_id = uuid.uuid4()
    file_path = "app/services/aws_client.py"

    # Line 2 contains an AWS Access Key ID
    source_code = (
        "# AWS Cloud Configuration\n"
        'api_key = "AKIA1234567890ABCDEF"\n'
        "def connect():\n"
        "    pass\n"
    )

    # Run audit_security which coordinates regex secrets + Semgrep + deduplication
    findings = AuditEngine.audit_security(
        project_id=project_id,
        file_path=file_path,
        source_code=source_code,
    )

    # Filter findings on line 2
    line_2_findings = [f for f in findings if f.location.start_line == 2]

    # Must be merged into ONE finding, not duplicated!
    assert len(line_2_findings) == 1, f"Expected exactly 1 merged finding on line 2, got {len(line_2_findings)}"

    merged = line_2_findings[0]
    assert merged.category == AuditCategory.SECURITY_VULNERABILITY
    assert merged.severity == AuditSeverity.CRITICAL

    # Both tools must be recorded in detected_by!
    assert "codesentinel-secrets-detector" in merged.detected_by
    if semgrep_scanner.is_available():
        assert "semgrep" in merged.detected_by
        assert merged.detected_by == ["codesentinel-secrets-detector", "semgrep"]


def test_correlator_unit_deduplication():
    """Unit test for FindingCorrelator with synthetic overlapping findings."""
    project_id = uuid.uuid4()

    finding_regex = AuditFinding(
        id=uuid.uuid4(),
        project_id=project_id,
        rule_id="SEC-SECRET-AWS-KEY",
        title="Hardcoded Credential Detected: AWS Access Key ID",
        description="Potential hardcoded credential or private token found matching 'AWS Access Key ID'.",
        category=AuditCategory.SECURITY_VULNERABILITY,
        severity=AuditSeverity.CRITICAL,
        standard=ComplianceStandard.OWASP_TOP_10,
        standard_reference_id="A07:2021-Identification and Authentication Failures",
        location=CodeLocation(file_path="app/config.py", start_line=15, end_line=15),
        remediation_suggestion="Revoke AWS credentials immediately.",
        status=AuditStatus.OPEN,
        cvss_score=8.5,
        detected_by=["codesentinel-secrets-detector"],
    )

    finding_semgrep = AuditFinding(
        id=uuid.uuid4(),
        project_id=project_id,
        rule_id="SEMGREP-PYTHON-LANG-SECURITY-HARDCODED-SECRET",
        title="Security Flaw: Hardcoded Secret",
        description="Hardcoded credential literal detected in source code. (Rule: python.lang.security.hardcoded-secret)",
        category=AuditCategory.SECURITY_VULNERABILITY,
        severity=AuditSeverity.HIGH,
        standard=ComplianceStandard.CWE,
        standard_reference_id="CWE-798",
        location=CodeLocation(file_path="app/config.py", start_line=15, end_line=15),
        remediation_suggestion="Extract secrets to environment variables.",
        status=AuditStatus.OPEN,
        cvss_score=7.5,
        detected_by=["semgrep"],
    )

    # Correlate
    result = FindingCorrelator.correlate_and_deduplicate([finding_regex, finding_semgrep])

    assert len(result) == 1, "Should deduplicate into a single correlated finding"
    unified = result[0]
    assert unified.detected_by == ["codesentinel-secrets-detector", "semgrep"]
    assert unified.severity == AuditSeverity.CRITICAL  # Elevated to highest
    assert unified.cvss_score == 8.5  # Elevated to highest
    assert unified.location.start_line == 15
    assert unified.location.end_line == 15
    assert "Correlated across 2 tools" in unified.description


def test_non_overlapping_findings_remain_distinct():
    """Verify findings on different lines or files are not merged."""
    project_id = uuid.uuid4()

    f1 = AuditFinding(
        id=uuid.uuid4(),
        project_id=project_id,
        rule_id="SEC-001",
        title="Secret on line 10",
        description="Secret",
        category=AuditCategory.SECURITY_VULNERABILITY,
        severity=AuditSeverity.HIGH,
        location=CodeLocation(file_path="app/auth.py", start_line=10, end_line=10),
        detected_by=["semgrep"],
    )

    f2 = AuditFinding(
        id=uuid.uuid4(),
        project_id=project_id,
        rule_id="SEC-002",
        title="Eval on line 50",
        description="Eval call",
        category=AuditCategory.SECURITY_VULNERABILITY,
        severity=AuditSeverity.CRITICAL,
        location=CodeLocation(file_path="app/auth.py", start_line=50, end_line=50),
        detected_by=["semgrep"],
    )

    result = FindingCorrelator.correlate_and_deduplicate([f1, f2])
    assert len(result) == 2, "Distinct line ranges must remain separate findings"


def test_dependency_scanner_reporting():
    """Verify DependencyVulnerabilityScanner detects outdated package vulnerabilities."""
    scanner = DependencyVulnerabilityScanner()
    project_id = uuid.uuid4()

    dependencies = [
        {"name": "urllib3", "version": "1.26.4"},
        {"name": "requests", "version": "2.30.0"},
    ]

    findings = scanner.scan_dependencies(
        project_id=project_id,
        dependencies=dependencies,
    )

    assert len(findings) >= 2
    for f in findings:
        assert f.category == AuditCategory.SECURITY_VULNERABILITY
        assert len(f.detected_by) == 1
        assert f.detected_by[0] in ("pip-audit", "codesentinel-dependency-advisory")
