"""
CodeSentinel Module 5 Tests: Analytics & Health Score Engine (Tests 8-10).

Verifies:
8. Pass rate broken down by provenance tier (REQUIREMENT_VERIFIED, SCHEMA_DERIVED, COVERAGE_ONLY, AI_INFERRED).
9. Project health score computed with exact formula logic and component weights.
10. Traceability matrix joins Requirement -> Module -> Code -> Test -> Execution -> Result.
"""

import pytest
import uuid
from typing import Any, Dict, List

from shared.schemas.test_case import TestCase, TestProvenance, TestStatus, TestType
from shared.schemas.test_execution import ExecutionStatus
from app.analytics.engine import AnalyticsEngine

# Suppress pytest collection warning on schemas
TestCase.__test__ = False
TestProvenance.__test__ = False
TestStatus.__test__ = False
TestType.__test__ = False


# ------------------------------------------------------------------------------
# Test 8: Pass Rate Broken Down by Provenance Tier
# ------------------------------------------------------------------------------
def test_pass_rate_broken_down_by_provenance_tier():
    """Test 8: Pass rate broken down by provenance tier against known fixture mix."""
    tc1_id, tc2_id = uuid.uuid4(), uuid.uuid4()
    tc3_id, tc4_id = uuid.uuid4(), uuid.uuid4()
    tc5_id = uuid.uuid4()

    test_cases = [
        {"id": str(tc1_id), "name": "tc1_req", "provenance": "REQUIREMENT_VERIFIED"},
        {"id": str(tc2_id), "name": "tc2_req", "provenance": "REQUIREMENT_VERIFIED"},
        {"id": str(tc3_id), "name": "tc3_schema", "provenance": "SCHEMA_DERIVED"},
        {"id": str(tc4_id), "name": "tc4_cov", "provenance": "COVERAGE_ONLY"},
        {"id": str(tc5_id), "name": "tc5_ai", "provenance": "AI_INFERRED"},
    ]

    # Executions:
    # REQUIREMENT_VERIFIED: tc1 PASSED, tc2 FAILED -> 1/2 = 50.0%
    # SCHEMA_DERIVED: tc3 PASSED -> 1/1 = 100.0%
    # COVERAGE_ONLY: tc4 FAILED -> 0/1 = 0.0%
    # AI_INFERRED: tc5 PASSED -> 1/1 = 100.0%
    # Total: 3 passed of 5 runs = 60.0%
    executions = [
        {
            "id": str(uuid.uuid4()),
            "results": [
                {"test_case_id": str(tc1_id), "status": "PASSED"},
                {"test_case_id": str(tc2_id), "status": "FAILED"},
                {"test_case_id": str(tc3_id), "status": "PASSED"},
                {"test_case_id": str(tc4_id), "status": "FAILED"},
                {"test_case_id": str(tc5_id), "status": "PASSED"},
            ]
        }
    ]

    rates = AnalyticsEngine.compute_tiered_pass_rates(test_cases, executions)

    # 1. Overall pass rate: 3/5 = 60.0%
    assert rates["overall_pass_rate_pct"] == 60.0, f"Expected 60.0%, got {rates['overall_pass_rate_pct']}"
    assert rates["total_executions"] == 5
    assert rates["total_passed"] == 3

    # 2. Breakdown per tier
    by_prov = rates["by_provenance"]
    assert by_prov["REQUIREMENT_VERIFIED"]["total_runs"] == 2
    assert by_prov["REQUIREMENT_VERIFIED"]["passed"] == 1
    assert by_prov["REQUIREMENT_VERIFIED"]["failed"] == 1
    assert by_prov["REQUIREMENT_VERIFIED"]["pass_rate_pct"] == 50.0

    assert by_prov["SCHEMA_DERIVED"]["total_runs"] == 1
    assert by_prov["SCHEMA_DERIVED"]["passed"] == 1
    assert by_prov["SCHEMA_DERIVED"]["pass_rate_pct"] == 100.0

    assert by_prov["COVERAGE_ONLY"]["total_runs"] == 1
    assert by_prov["COVERAGE_ONLY"]["passed"] == 0
    assert by_prov["COVERAGE_ONLY"]["pass_rate_pct"] == 0.0

    assert by_prov["AI_INFERRED"]["total_runs"] == 1
    assert by_prov["AI_INFERRED"]["passed"] == 1
    assert by_prov["AI_INFERRED"]["pass_rate_pct"] == 100.0


# ------------------------------------------------------------------------------
# Test 9: Health Score Exact Formula Computation
# ------------------------------------------------------------------------------
def test_health_score_formula_exact_computation():
    """
    Test 9: Health score - pure deterministic formula computation.
    Formula:
      HealthScore = 0.35 * ReqCoverage + 0.25 * ReqPassRate + 0.15 * Quality + 0.15 * Security + 0.10 * Architecture

    Input:
      req_coverage_pct = 80.0
      req_pass_rate_pct = 90.0
      critical_vulns = 1 (penalty: 1 * 25 = 25 -> Security = 75.0)
      high_vulns = 0, medium_vulns = 0
      high_cc_count = 1 (penalty: 1 * 10 = 10 -> Quality = 90.0)
      duplication_count = 0, smell_count = 0
      circular_dep_count = 0, layer_violation_count = 0 -> Architecture = 100.0

    Manual calculation:
      0.35 * 80.0  = 28.0
      0.25 * 90.0  = 22.5
      0.15 * 90.0  = 13.5
      0.15 * 75.0  = 11.25
      0.10 * 100.0 = 10.0
      Total = 28.0 + 22.5 + 13.5 + 11.25 + 10.0 = 85.25 -> rounded to 1 decimal: 85.3
    """
    health = AnalyticsEngine.calculate_health_score(
        req_coverage_pct=80.0,
        req_pass_rate_pct=90.0,
        critical_vulns=1,
        high_vulns=0,
        medium_vulns=0,
        high_cc_count=1,
        duplication_count=0,
        smell_count=0,
        circular_dep_count=0,
        layer_violation_count=0,
    )

    # Assert exact computed health score matches manual calculation (85.25 -> rounded banker's 85.2)
    assert health["health_score"] == 85.2, f"Expected 85.2, got {health['health_score']}"
    assert health["grade"] == "B"

    # Assert component breakdown exposes distinct values
    comps = health["components"]
    assert comps["requirement_coverage"]["score"] == 80.0
    assert comps["requirement_pass_rate"]["score"] == 90.0
    assert comps["code_quality"]["score"] == 90.0
    assert comps["security"]["score"] == 75.0
    assert comps["architecture"]["score"] == 100.0


# ------------------------------------------------------------------------------
# Test 10: Traceability Matrix Joins
# ------------------------------------------------------------------------------
def test_traceability_matrix_structure_and_joins():
    """
    Test 10: Traceability matrix - joins Requirement -> Module -> Code -> Test -> Execution -> Result.
    """
    req_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    test_id = uuid.uuid4()
    exec_id = uuid.uuid4()

    requirements = [
        {"id": str(req_id), "identifier": "REQ-PAY-01", "title": "Payment Processing"}
    ]
    entities = [
        {"id": str(entity_id), "name": "charge_credit_card", "file_path": "payments/gateway.py"}
    ]
    test_cases = [
        {
            "id": str(test_id),
            "name": "test_charge_credit_card_valid",
            "provenance": "REQUIREMENT_VERIFIED",
            "requirement_id": str(req_id),
            "target_entity_id": str(entity_id),
            "file_path": "tests/test_payments.py",
        }
    ]
    executions = [
        {
            "id": str(exec_id),
            "created_at": "2026-09-03T10:00:00Z",
            "results": [
                {
                    "test_case_id": str(test_id),
                    "status": "PASSED",
                    "duration_ms": 42.5,
                }
            ]
        }
    ]

    matrix = AnalyticsEngine.build_traceability_matrix(
        requirements=requirements,
        entities=entities,
        test_cases=test_cases,
        executions=executions,
    )

    assert len(matrix) == 1, f"Expected 1 traceability entry, got {len(matrix)}"
    row = matrix[0]

    # Verify end-to-end joined fields
    assert row["requirement_identifier"] == "REQ-PAY-01"
    assert row["requirement_title"] == "Payment Processing"
    assert row["module"] == "payments"
    assert row["entity_name"] == "charge_credit_card"
    assert row["entity_file_path"] == "payments/gateway.py"
    assert row["test_name"] == "test_charge_credit_card_valid"
    assert row["provenance"] == "REQUIREMENT_VERIFIED"
    assert row["execution_status"] == "PASSED"
    assert row["duration_ms"] == 42.5


# ------------------------------------------------------------------------------
# Test 11: FIX 5 - Unevaluated Components & No Fallback Bug
# ------------------------------------------------------------------------------
def test_health_score_unevaluated_components_and_no_fallback():
    """
    Test FIX 5:
    1. Zero runs for REQUIREMENT_VERIFIED must NOT fallback to overall_pass_rate_pct.
    2. Unevaluated components score 0.0 with evaluated=False.
    3. If nothing has been evaluated, grade is 'Not yet evaluated'.
    4. Audited clean project with 0 findings scores 100% with evaluated=True.
    """
    # Case A: Brand new project, nothing evaluated yet
    health_new = AnalyticsEngine.calculate_health_score(
        req_coverage_pct=0.0,
        req_pass_rate_pct=0.0,
        req_coverage_evaluated=False,
        req_pass_rate_evaluated=False,
        quality_evaluated=False,
        security_evaluated=False,
        architecture_evaluated=False,
    )
    assert health_new["health_score"] == 0.0
    assert health_new["grade"] == "Not yet evaluated"
    assert health_new["evaluated"] is False
    for comp in health_new["components"].values():
        assert comp["score"] == 0.0
        assert comp["evaluated"] is False

    # Case B: Tests ran (e.g. SCHEMA_DERIVED 100% passed), but REQUIREMENT_VERIFIED has 0 runs
    # In old code, req_pass_rate substituted 100% from overall_pass_rate_pct.
    # In FIX 5, req_pass_rate must be 0.0 with evaluated=False.
    health_no_req_run = AnalyticsEngine.calculate_health_score(
        req_coverage_pct=100.0,
        req_pass_rate_pct=0.0,
        req_coverage_evaluated=True,
        req_pass_rate_evaluated=False, # 0 runs for REQUIREMENT_VERIFIED
        quality_evaluated=True,
        security_evaluated=True,
        architecture_evaluated=True,
    )
    # Req Coverage (35% of 100 = 35) + Req Pass Rate (0 because evaluated=False) + Quality (15) + Sec (15) + Arch (10) = 75.0
    assert health_no_req_run["components"]["requirement_pass_rate"]["score"] == 0.0
    assert health_no_req_run["components"]["requirement_pass_rate"]["evaluated"] is False
    assert health_no_req_run["health_score"] == 75.0
    assert health_no_req_run["grade"] == "C"

    # Case C: Clean audited project (0 findings because clean, NOT because never scanned)
    health_clean = AnalyticsEngine.calculate_health_score(
        req_coverage_pct=100.0,
        req_pass_rate_pct=100.0,
        critical_vulns=0,
        high_vulns=0,
        medium_vulns=0,
        high_cc_count=0,
        duplication_count=0,
        smell_count=0,
        circular_dep_count=0,
        layer_violation_count=0,
        req_coverage_evaluated=True,
        req_pass_rate_evaluated=True,
        quality_evaluated=True,
        security_evaluated=True,
        architecture_evaluated=True,
    )
    assert health_clean["health_score"] == 100.0
    assert health_clean["grade"] == "A"
    assert health_clean["components"]["security"]["score"] == 100.0
    assert health_clean["components"]["security"]["evaluated"] is True
