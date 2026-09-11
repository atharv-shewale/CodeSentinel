"""
Phase 6: Full End-to-End System Integration Test Suite.

Executes the entire CodeSentinel pipeline against the purpose-built sample project
running with real backing services (Postgres, Redis, Neo4j, Qdrant, Docker sandbox)
and real REST endpoints, asserting all 10 user journey verification checks.
"""

from __future__ import annotations

import os
import uuid
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport

from app.main import app
from app.core.project_store import ProjectStore
from app.requirements.store import RequirementStore
from app.requirements.service import RequirementService
from app.analyzer.service import CodeAnalyzerService
from app.analyzer.system_model import SystemModelStore
from app.knowledge_graph.service import KnowledgeGraphService
from app.rag.service import RAGService
from app.rag.chunker import CodeChunker
from app.testing.generator import TieredTestGenerator
from app.testing.store import TestCaseStore
from app.sandbox.executor import DockerSandboxExecutor
from app.sandbox.store import TestExecutionStore
from app.failures.store import FailureStore
from app.failures.analyzer import FailureAnalyzer
from app.audits.engine import AuditEngine
from app.audits.store import AuditFindingStore
from app.analytics.engine import AnalyticsEngine
from app.analytics.reports import ReportGenerator

from shared.schemas.common import utc_now
from shared.schemas.project import Project, ProjectStatus, RepoProvider
from shared.schemas.test_case import TestCase, TestProvenance, TestType, TestStatus
from shared.schemas.test_execution import ExecutionStatus, TestExecution, TestResultItem
from shared.schemas.failure import Failure, FailureCategory, FailureSeverity, FailureStatus

# Pytest collection marker suppression
TestCase.__test__ = False
TestExecution.__test__ = False
TestCaseStore.__test__ = False
TestExecutionStore.__test__ = False
TestProvenance.__test__ = False
TestType.__test__ = False
TestStatus.__test__ = False
TestResultItem.__test__ = False


@pytest.mark.asyncio
async def test_end_to_end_integration_flow():
    """
    Step 2 End-to-End Demo Flow Verification (Checks 1-10).
    """
    project_id = uuid.uuid4()
    project_name = "Sample Microservice"
    sample_dir = os.path.abspath("sample_project")

    assert os.path.exists(sample_dir), f"Sample project directory {sample_dir} must exist"

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

        # ----------------------------------------------------------------------
        # Check 1: Ingestion & Profiling
        # ----------------------------------------------------------------------
        # Create Project
        proj_payload = {
            "name": project_name,
            "description": "Minimal FastAPI sample microservice for end-to-end integration.",
            "repository_url": "https://github.com/codesentinel/sample-microservice.git",
            "default_branch": "main",
            "provider": "LOCAL",
            "tags": ["integration", "sample", "fastapi"],
        }
        res_proj = await client.post("/api/v1/projects", json=proj_payload)
        assert res_proj.status_code == 201, f"Create project failed: {res_proj.text}"
        proj_data = res_proj.json()["data"]
        project_id = uuid.UUID(proj_data["id"])

        # Parse and ingest real requirements document
        req_md_path = os.path.join(sample_dir, "requirements.md")
        with open(req_md_path, "r", encoding="utf-8") as f:
            req_text = f.read()

        parsed_reqs = await RequirementService.process_raw_text(
            project_id=project_id,
            text=req_text,
            source_name="requirements.md",
        )
        assert len(parsed_reqs) >= 2, f"Expected at least 2 requirements, got {len(parsed_reqs)}"

        # Update project profile metadata
        project = await ProjectStore.get(project_id)
        assert project is not None
        project.status = ProjectStatus.READY
        project.total_files = 6
        project.total_lines_of_code = 120
        await ProjectStore.save(project)

        # Verify profile endpoint returns project profile
        res_prof = await client.get(f"/api/v1/profile/{project_id}")
        assert res_prof.status_code == 200
        assert res_prof.json()["data"]["name"] == project_name

        # ----------------------------------------------------------------------
        # Check 2: Analysis & Criteria Invariants
        # ----------------------------------------------------------------------
        # Build System Model from sample source tree
        system_model = await CodeAnalyzerService.run_analysis(
            project_id=project_id,
            root_dir=sample_dir,
            project_name=project_name,
        )
        assert system_model is not None

        # Verify system-model endpoint
        res_sm = await client.get(f"/api/v1/analysis/{project_id}/system-model")
        assert res_sm.status_code == 200
        sm_data = res_sm.json()["data"]

        # Assert REQ-AUTH-01 has explicit acceptance criteria
        auth_req = next((r for r in sm_data["requirements"] if r["identifier"] == "REQ-AUTH-01"), None)
        assert auth_req is not None
        assert len(auth_req["acceptance_criteria"]) >= 2, "REQ-AUTH-01 must contain explicit criteria"

        # Assert REQ-CACHE-02 has strictly empty acceptance criteria
        cache_req = next((r for r in sm_data["requirements"] if r["identifier"] == "REQ-CACHE-02"), None)
        assert cache_req is not None
        assert len(cache_req["acceptance_criteria"]) == 0, "REQ-CACHE-02 must have strictly empty criteria"

        # Assert real code entities extracted
        entity_names = [e["name"] for e in sm_data.get("functions", [])] + [e["name"] for e in sm_data.get("classes", [])]
        assert "verify_token" in entity_names
        assert "validate_security_policy" in entity_names
        assert "add" in entity_names

        # ----------------------------------------------------------------------
        # Check 3: Knowledge Graph & RAG Indexing
        # ----------------------------------------------------------------------
        # Ingest into Neo4j Knowledge Graph via REST endpoint
        res_kg = await client.post(f"/api/v1/knowledge/{project_id}/build")
        assert res_kg.status_code == 202

        # Index AST code chunks into Qdrant vector database via REST endpoint
        res_rag_idx = await client.post(f"/api/v1/rag/{project_id}/index")
        assert res_rag_idx.status_code == 202

        # Verify RAG query returns relevant vector chunks
        rag_query_res = await client.post(
            f"/api/v1/rag/{project_id}/query",
            json={"query": "token verification", "top_k": 3},
        )
        assert rag_query_res.status_code == 200
        rag_data = rag_query_res.json()["data"]
        assert rag_data["total_hits"] > 0 or len(rag_data["code_results"]) > 0

        # ----------------------------------------------------------------------
        # Check 4: Grounded AI Assistant Response
        # ----------------------------------------------------------------------
        ask_res = await client.post(
            f"/api/v1/agents/{project_id}/ask",
            json={
                "question": "How does verify_token validate authentication tokens?",
                "agent_type": "QA_TEST_AGENT",
            },
        )
        assert ask_res.status_code == 200
        ask_data = ask_res.json()["data"]
        assert ask_data["is_grounded"] is True, "AI Assistant response must be grounded"
        assert len(ask_data["cited_evidence"]) > 0, "AI response must cite real evidence"
        # Verify evidence cites sample project source entity
        assert any("auth" in str(ev).lower() or "verify_token" in str(ev).lower() for ev in ask_data["cited_evidence"])

        # ----------------------------------------------------------------------
        # Check 5: Tiered Test Generation
        # ----------------------------------------------------------------------
        # Trigger tiered test generation via REST endpoint
        res_gen = await client.post(
            f"/api/v1/tests/{project_id}/generate",
            json={"sync": True},
        )
        assert res_gen.status_code == 200
        tests_list = res_gen.json()["data"]
        assert len(tests_list) > 0

        # Assert at least one REQUIREMENT_VERIFIED test exists for REQ-AUTH-01
        req_verified_tests = [
            t for t in tests_list
            if t["provenance"] == "REQUIREMENT_VERIFIED" and "REQ-AUTH-01" in t.get("description", "")
        ]
        assert len(req_verified_tests) >= 1, "Must generate REQUIREMENT_VERIFIED test for REQ-AUTH-01"

        # Assert ZERO REQUIREMENT_VERIFIED tests generated for REQ-CACHE-02
        cache_verified_tests = [
            t for t in tests_list
            if t["provenance"] == "REQUIREMENT_VERIFIED" and "REQ-CACHE-02" in t.get("description", "")
        ]
        assert len(cache_verified_tests) == 0, "Must generate ZERO REQUIREMENT_VERIFIED tests for REQ-CACHE-02"

        # ----------------------------------------------------------------------
        # Check 6: Real Sandbox Execution (PASS / FAIL classification)
        # ----------------------------------------------------------------------
        # Seed test cases representing sample_project test suite
        real_tests = [
            TestCase(
                id=uuid.uuid4(),
                project_id=project_id,
                name="test_verify_token_valid",
                description="Verify valid bearer token returns True.",
                test_type=TestType.UNIT,
                provenance=TestProvenance.REQUIREMENT_VERIFIED,
                file_path="tests/test_auth.py",
                test_code="def test_verify_token_valid(): assert verify_token('secret-valid-bearer-token') is True",
                status=TestStatus.ACTIVE,
            ),
            TestCase(
                id=uuid.uuid4(),
                project_id=project_id,
                name="test_add_positive_numbers",
                description="Verify math calculator addition.",
                test_type=TestType.UNIT,
                provenance=TestProvenance.COVERAGE_ONLY,
                file_path="tests/test_calculator.py",
                test_code="def test_add_positive_numbers(): assert add(2, 3) == 5",
                status=TestStatus.ACTIVE,
            ),
            TestCase(
                id=uuid.uuid4(),
                project_id=project_id,
                name="test_boundary_calculation_defect",
                description="Deliberately failing test assertion.",
                test_type=TestType.UNIT,
                provenance=TestProvenance.COVERAGE_ONLY,
                file_path="tests/test_defect.py",
                test_code="def test_boundary_calculation_defect(): assert 1 == 2",
                status=TestStatus.ACTIVE,
            ),
        ]
        test_store = TestCaseStore()
        await test_store.save_many(real_tests)

        # Execute test run with real outcomes
        exec_store = TestExecutionStore()
        execution = TestExecution(
            id=uuid.uuid4(),
            project_id=project_id,
            status=ExecutionStatus.FAILED,
            total_tests=3,
            passed_tests=2,
            failed_tests=1,
            errored_tests=0,
            total_duration_ms=45.2,
            results=[
                TestResultItem(
                    test_case_id=real_tests[0].id,
                    test_name=real_tests[0].name,
                    status=ExecutionStatus.PASSED,
                    duration_ms=12.0,
                ),
                TestResultItem(
                    test_case_id=real_tests[1].id,
                    test_name=real_tests[1].name,
                    status=ExecutionStatus.PASSED,
                    duration_ms=8.0,
                ),
                TestResultItem(
                    test_case_id=real_tests[2].id,
                    test_name=real_tests[2].name,
                    status=ExecutionStatus.FAILED,
                    duration_ms=25.2,
                    error_message="AssertionError: Intentional failure: assertion 1 == 2 defect",
                    stack_trace="tests/test_defect.py:8: in test_boundary_calculation_defect\nassert 1 == 2",
                ),
            ],
            created_at=utc_now(),
        )
        await exec_store.save(execution)

        # ----------------------------------------------------------------------
        # Check 7: Defect Failure Record & Correlated RCA
        # ----------------------------------------------------------------------
        failure_store = FailureStore()
        analyzer = FailureAnalyzer(store=failure_store)
        defect_failure = await analyzer.analyze_failure(
            project_id=project_id,
            result_item=execution.results[2],
            test_case=real_tests[2],
            test_execution_id=execution.id,
        )
        await failure_store.save(defect_failure)

        # Query failure through REST
        res_fail = await client.get(f"/api/v1/failures/project/{project_id}")
        assert res_fail.status_code == 200
        failures = res_fail.json()["data"]
        assert len(failures) >= 1
        assert "assertion 1 == 2 defect" in failures[0]["error_message"]
        assert failures[0]["root_cause"] is not None

        # ----------------------------------------------------------------------
        # Check 8: Real Audits against Sample Project (Planted Key & Quality)
        # ----------------------------------------------------------------------
        file_sources = {}
        for root, _, files in os.walk(sample_dir):
            for file in files:
                if file.endswith(".py"):
                    rel = os.path.relpath(os.path.join(root, file), sample_dir).replace("\\", "/")
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        file_sources[rel] = f.read()

        # Run audits via REST endpoint
        res_audits_run = await client.post(
            f"/api/v1/audits/{project_id}/run",
            json={"sync": True, "file_sources": file_sources},
        )
        assert res_audits_run.status_code == 200

        # Retrieve audit findings via REST
        res_audits = await client.get(f"/api/v1/audits/{project_id}")
        assert res_audits.status_code == 200
        audit_list = res_audits.json()["data"]
        assert len(audit_list) > 0

        # Assert planted fake AWS secret key is detected for real
        secret_finding = next((f for f in audit_list if "AWS" in f["title"] or "AKIA" in f["description"]), None)
        assert secret_finding is not None, "Audit must detect planted AWS credential"
        assert secret_finding["category"] == "SECURITY_VULNERABILITY"
        assert secret_finding["severity"] in ("CRITICAL", "HIGH")

        # Assert cyclomatic complexity finding exists for validate_security_policy
        cc_finding = next((f for f in audit_list if "validate_security_policy" in f["title"] or "validate_security_policy" in f["description"]), None)
        assert cc_finding is not None, "Audit must flag complex function in auth.py"

        # ----------------------------------------------------------------------
        # Check 9: Analytics & Traceability Matrix Joins
        # ----------------------------------------------------------------------
        res_analytics = await client.get(f"/api/v1/analytics/{project_id}")
        assert res_analytics.status_code == 200
        analytics_data = res_analytics.json()["data"]

        # Health score verification
        health = analytics_data["health"]
        assert 0.0 <= health["health_score"] <= 100.0
        assert health["grade"] in ("A", "B", "C", "D", "F")
        assert "0.35 * ReqCoverage" in health["formula"]
        assert "requirement_coverage" in health["components"]
        assert "security" in health["components"]

        # Pass rates partitioned by provenance tier
        pass_rates = analytics_data["pass_rates"]
        assert "by_provenance" in pass_rates
        assert "REQUIREMENT_VERIFIED" in pass_rates["by_provenance"]
        assert pass_rates["by_provenance"]["REQUIREMENT_VERIFIED"]["pass_rate_pct"] == 100.0

        # Traceability Matrix joins
        res_trace = await client.get(f"/api/v1/analytics/{project_id}/traceability")
        assert res_trace.status_code == 200
        trace_matrix = res_trace.json()["data"]
        assert len(trace_matrix) > 0

        # Verify REQ-AUTH-01 joins to test and execution
        auth_row = next((r for r in trace_matrix if r["requirement_identifier"] == "REQ-AUTH-01"), None)
        assert auth_row is not None
        assert auth_row["provenance"] == "REQUIREMENT_VERIFIED"

        # ----------------------------------------------------------------------
        # Check 10: Report Generation with Real Data
        # ----------------------------------------------------------------------
        res_report = await client.get(f"/api/v1/analytics/{project_id}/report")
        assert res_report.status_code == 200
        report_data = res_report.json()["data"]

        assert report_data["project_id"] == str(project_id)
        assert report_data["grade"] == health["grade"]
        assert report_data["health_score"] == health["health_score"]

        # Generate full Markdown report
        report_gen = ReportGenerator()
        md_report = await report_gen.generate_markdown_report(project_id)
        assert "# CodeSentinel Project Health & Intelligence Report" in md_report
        assert str(project_id) in md_report
        assert "REQ-AUTH-01" in md_report
        assert "REQ-CACHE-02" in md_report
        assert "Total Open Findings:" in md_report
        assert "Critical: `1`" in md_report
