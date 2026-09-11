"""
CodeSentinel Module 5 Tests: Audit Engine Deterministic Verifications (Tests 1-7).

Verifies:
1. Code Quality: cyclomatic complexity exact value match on fixture.
2. Code Quality: duplicated code block detection.
3. Security: hardcoded secret detection with severity and file/line location.
4. Security: vulnerable dependency flagged from dependency list.
5. Coverage: requirement, code, and API coverage percentages exact computation.
6. Coverage: code coverage reported strictly per-language, NEVER unified.
7. Architecture: circular import dependency detected in import graph.
"""

import pytest
import uuid
from typing import Any, Dict, List

from shared.schemas.audit import (
    AuditCategory,
    AuditFinding,
    AuditSeverity,
    AuditStatus,
)
from app.audits.engine import AuditEngine

# Suppress pytest collection warning on schemas
AuditFinding.__test__ = False


# ------------------------------------------------------------------------------
# Test 1: Cyclomatic Complexity Exact Value Match
# ------------------------------------------------------------------------------
def test_code_quality_cyclomatic_complexity_exact():
    """
    Test 1: Code quality - fixture function with known cyclomatic complexity.
    Complexity = 1 (base) + 4 decisions (if, elif, for, and) = 5.
    """
    project_id = uuid.uuid4()
    file_path = "services/billing.py"

    # Known cyclomatic complexity = 5:
    # 1 (base) + 1 (if amount > 1000) + 1 (elif amount > 500) + 1 (for item in items) + 1 (and item.taxable)
    code = '''
def calculate_discount(amount, items):
    discount = 0.0
    if amount > 1000:
        discount = 0.20
    elif amount > 500:
        discount = 0.10
    for item in items:
        if item.is_active and item.taxable:
            discount += 0.01
    return discount
'''
    import radon.complexity as radon_cc
    blocks = radon_cc.cc_visit(code)
    assert len(blocks) == 1
    # Assert exact computed cyclomatic complexity value is 6 (1 base + if + elif + for + if + and)
    assert blocks[0].complexity == 6, f"Expected exact cyclomatic complexity of 6, got {blocks[0].complexity}"

    # Now verify high complexity threshold triggers finding
    high_cc_code = '''
def complex_dispatcher(x):
    if x == 1: return 1
    elif x == 2: return 2
    elif x == 3: return 3
    elif x == 4: return 4
    elif x == 5: return 5
    elif x == 6: return 6
    elif x == 7: return 7
    elif x == 8: return 8
    elif x == 9: return 9
    elif x == 10: return 10
    elif x == 11: return 11
    return 0
'''
    findings = AuditEngine.audit_code_quality(project_id, file_path, high_cc_code)
    cc_findings = [f for f in findings if f.rule_id == "QUAL-COMPLEXITY-HIGH"]
    assert len(cc_findings) == 1
    assert "High Cyclomatic Complexity (12)" in cc_findings[0].title
    assert cc_findings[0].location.file_path == file_path


# ------------------------------------------------------------------------------
# Test 2: Deliberately Duplicated Code Block
# ------------------------------------------------------------------------------
def test_code_quality_duplication_detected():
    """Test 2: Code quality - fixture with a deliberately duplicated code block."""
    project_id = uuid.uuid4()
    file_path = "services/processor.py"

    code = '''
def process_alpha(data):
    x = data.get("a", 0)
    y = data.get("b", 0)
    total = x + y
    scaled = total * 1.5
    normalized = scaled / 100.0
    result = {"value": normalized, "valid": True}
    return result

def process_beta(data):
    x = data.get("a", 0)
    y = data.get("b", 0)
    total = x + y
    scaled = total * 1.5
    normalized = scaled / 100.0
    result = {"value": normalized, "valid": True}
    return result
'''
    findings = AuditEngine.audit_code_quality(project_id, file_path, code)
    dup_findings = [f for f in findings if f.rule_id == "QUAL-DUPLICATION-DETECTED"]

    assert len(dup_findings) >= 1, "Expected at least 1 duplicate block finding"
    assert dup_findings[0].category == AuditCategory.CODE_SMELL
    assert dup_findings[0].severity == AuditSeverity.MEDIUM
    assert dup_findings[0].location.file_path == file_path


# ------------------------------------------------------------------------------
# Test 3: Hardcoded Fake API Key
# ------------------------------------------------------------------------------
def test_security_hardcoded_api_key_detected():
    """Test 3: Security - fixture with hardcoded AWS key and GitHub token."""
    project_id = uuid.uuid4()
    file_path = "config/credentials.py"

    code = '''# Configuration module
import os

AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"
GITHUB_ACCESS_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
DATABASE_URL = "postgresql://localhost:5432/db"
'''
    findings = AuditEngine.audit_security(project_id, file_path, code)

    aws_findings = [f for f in findings if f.rule_id == "SEC-SECRET-AWS-KEY"]
    assert len(aws_findings) == 1, "Expected AWS Access Key detection"
    assert aws_findings[0].severity == AuditSeverity.CRITICAL
    assert aws_findings[0].location.file_path == file_path
    assert aws_findings[0].location.start_line == 4
    assert aws_findings[0].location.end_line == 4
    assert "Revoke AWS credentials" in aws_findings[0].remediation_suggestion

    github_findings = [f for f in findings if f.rule_id == "SEC-SECRET-GITHUB-PAT"]
    assert len(github_findings) == 1, "Expected GitHub PAT detection"
    assert github_findings[0].severity == AuditSeverity.CRITICAL
    assert github_findings[0].location.start_line == 5


# ------------------------------------------------------------------------------
# Test 4: Vulnerable Dependency
# ------------------------------------------------------------------------------
def test_security_vulnerable_dependency_flagged():
    """Test 4: Security - fixture dependency list with known-vulnerable package."""
    project_id = uuid.uuid4()
    file_path = "requirements.txt"

    dependencies = [
        {"name": "fastapi", "version": "0.110.0"},
        {"name": "urllib3", "version": "1.26.4"},  # Known vulnerable in snapshot
        {"name": "pydantic", "version": "2.6.0"},
        {"name": "pyyaml", "version": "5.3.1"},    # Known critical in snapshot
    ]

    findings = AuditEngine.audit_security(
        project_id=project_id,
        file_path=file_path,
        source_code="",
        dependencies=dependencies,
    )

    vuln_findings = [f for f in findings if "SEC-VULN-DEP" in f.rule_id]
    assert len(vuln_findings) >= 2, f"Expected at least 2 vulnerable dependencies flagged, got {len(vuln_findings)}"

    urllib_f = next(f for f in vuln_findings if "URLLIB3" in f.rule_id)
    assert urllib_f.severity == AuditSeverity.HIGH
    assert "CVE-2021-33503" in urllib_f.title

    yaml_f = next(f for f in vuln_findings if "PYYAML" in f.rule_id)
    assert yaml_f.severity == AuditSeverity.CRITICAL


# ------------------------------------------------------------------------------
# Test 5: Exact Coverage Percentage Computation
# ------------------------------------------------------------------------------
def test_coverage_percentages_compute_correctly():
    """Test 5: Coverage - assert requirement/API coverage computes exactly (e.g. 3 of 5 = 60%)."""
    project_id = uuid.uuid4()

    req_ids = [uuid.uuid4() for _ in range(5)]
    requirements = [
        {"id": str(r_id), "identifier": f"REQ-{idx}", "title": f"Req {idx}"}
        for idx, r_id in enumerate(req_ids, start=1)
    ]

    # Exactly 3 of 5 requirements have REQUIREMENT_VERIFIED tests
    test_cases = [
        {"id": uuid.uuid4(), "requirement_id": str(req_ids[0]), "provenance": "REQUIREMENT_VERIFIED"},
        {"id": uuid.uuid4(), "requirement_id": str(req_ids[1]), "provenance": "REQUIREMENT_VERIFIED"},
        {"id": uuid.uuid4(), "requirement_id": str(req_ids[2]), "provenance": "REQUIREMENT_VERIFIED"},
        # 4th test is AI_INFERRED, must NOT count towards REQUIREMENT_VERIFIED coverage
        {"id": uuid.uuid4(), "requirement_id": str(req_ids[3]), "provenance": "AI_INFERRED"},
    ]

    route_ids = [uuid.uuid4() for _ in range(4)]
    routes = [
        {"id": str(r_id), "path": f"/api/v1/res/{idx}", "method": "GET"}
        for idx, r_id in enumerate(route_ids, start=1)
    ]
    # Link test cases to 2 of 4 routes
    test_cases[0]["target_route_id"] = str(route_ids[0])
    test_cases[1]["target_route_id"] = str(route_ids[1])

    findings, metrics = AuditEngine.audit_test_coverage(
        project_id=project_id,
        requirements=requirements,
        routes=routes,
        entities=[],
        test_cases=test_cases,
    )

    # 3 of 5 requirements covered -> exactly 60.0%
    assert metrics["requirement_coverage_pct"] == 60.0, f"Expected 60.0%, got {metrics['requirement_coverage_pct']}"
    assert metrics["total_requirements"] == 5
    assert metrics["covered_requirements"] == 3
    assert len(metrics["uncovered_requirements"]) == 2

    # 2 of 4 routes tested -> exactly 50.0%
    assert metrics["api_coverage_pct"] == 50.0, f"Expected 50.0%, got {metrics['api_coverage_pct']}"
    assert metrics["total_routes"] == 4
    assert metrics["covered_routes"] == 2
    assert len(metrics["uncovered_routes"]) == 2


# ------------------------------------------------------------------------------
# Test 6: Code Coverage STRICTLY Per-Language, Never Unified
# ------------------------------------------------------------------------------
def test_code_coverage_reported_per_language_never_unified():
    """
    Test 6: Code coverage is reported PER LANGUAGE separately (e.g. Python: 66.67%, JS: 50.0%).
    INVARIANT: MUST NOT synthesize a single unified cross-language number!
    """
    project_id = uuid.uuid4()

    py_id1, py_id2, py_id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    js_id1, js_id2 = uuid.uuid4(), uuid.uuid4()

    entities = [
        {"id": str(py_id1), "name": "py_fn_1", "file_path": "backend/app/auth.py"},
        {"id": str(py_id2), "name": "py_fn_2", "file_path": "backend/app/tokens.py"},
        {"id": str(py_id3), "name": "py_fn_3", "file_path": "backend/app/users.py"},
        {"id": str(js_id1), "name": "fetchUser", "file_path": "frontend/src/api.ts"},
        {"id": str(js_id2), "name": "renderTable", "file_path": "frontend/src/table.tsx"},
    ]

    # Tests cover 2 of 3 Python functions, and 1 of 2 TS functions
    test_cases = [
        {"id": uuid.uuid4(), "target_entity_id": str(py_id1), "provenance": "UNIT"},
        {"id": uuid.uuid4(), "target_entity_id": str(py_id2), "provenance": "UNIT"},
        {"id": uuid.uuid4(), "target_entity_id": str(js_id1), "provenance": "UNIT"},
    ]

    findings, metrics = AuditEngine.audit_test_coverage(
        project_id=project_id,
        requirements=[],
        routes=[],
        entities=entities,
        test_cases=test_cases,
    )

    per_lang = metrics["code_coverage_per_language"]

    # Invariant checks:
    # 1. Must contain distinct entries for Python and JavaScript/TypeScript
    assert "Python" in per_lang, "Missing Python language coverage entry"
    assert "JavaScript/TypeScript" in per_lang, "Missing JavaScript/TypeScript language coverage entry"

    # 2. Values must be calculated independently:
    # Python: 2/3 = 66.67%
    assert per_lang["Python"] == 66.67, f"Expected Python coverage 66.67%, got {per_lang['Python']}"
    # JS/TS: 1/2 = 50.0%
    assert per_lang["JavaScript/TypeScript"] == 50.0, f"Expected JS coverage 50.0%, got {per_lang['JavaScript/TypeScript']}"

    # 3. Explicitly assert there is NO single unified "code_coverage_pct" key in metrics
    assert "code_coverage_pct" not in metrics, (
        "CRITICAL INVARIANT VIOLATION: Single unified cross-language code_coverage_pct was synthesized!"
    )


# ------------------------------------------------------------------------------
# Test 7: Circular Dependency Detection
# ------------------------------------------------------------------------------
def test_architecture_circular_import_detected():
    """Test 7: Architecture - fixture import graph with deliberate circular import."""
    project_id = uuid.uuid4()

    # Import graph with cycle: module_a -> module_b -> module_c -> module_a
    # and acyclic node: module_d -> module_c
    import_graph = {
        "app/services/orders.py": ["app/services/billing.py", "app/models/order.py"],
        "app/services/billing.py": ["app/services/notifications.py"],
        "app/services/notifications.py": ["app/services/orders.py"],  # Cycle!
        "app/models/order.py": [],
    }

    findings = AuditEngine.audit_architecture(project_id, import_graph)
    cycle_findings = [f for f in findings if f.rule_id == "ARCH-CIRCULAR-DEPENDENCY"]

    assert len(cycle_findings) >= 1, "Expected circular dependency detected"
    finding = cycle_findings[0]
    assert finding.category == AuditCategory.ARCHITECTURE_DRIFT
    assert finding.severity == AuditSeverity.HIGH
    assert "Circular Import Dependency Detected" in finding.title
    assert "app/services/orders.py" in finding.description
    assert "app/services/billing.py" in finding.description
    assert "app/services/notifications.py" in finding.description
