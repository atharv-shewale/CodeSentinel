"""
CodeSentinel Contract Validation Tests.

Validates that all shared Pydantic models in shared/schemas/ satisfy strict typing,
docstring presence, field serialization, and domain invariants (such as TestCase provenance).
"""

import uuid
import pytest
from pydantic import ValidationError

from shared.schemas.common import APIResponse, APIError, PaginationMeta, BaseEntity
from shared.schemas.project import Project, ProjectCreate, ProjectStatus, RepoProvider
from shared.schemas.requirement import Requirement, RequirementCreate, RequirementPriority, RequirementStatus, RequirementType
from shared.schemas.code_entity import CodeEntity, CodeLocation, EntityType, Visibility
from shared.schemas.api_route import APIRoute, AuthRequirement, HTTPMethod
from shared.schemas.test_case import TestCase, TestCaseCreate, TestProvenance, TestStatus, TestType
from shared.schemas.test_execution import TestExecution, ExecutionStatus, ExecutionEnvironment
from shared.schemas.failure import Failure, FailureCategory, FailureSeverity, FailureStatus, RootCauseAnalysis
from shared.schemas.audit import AuditFinding, AuditCategory, AuditSeverity, AuditStatus, ComplianceStandard
from shared.schemas.jobs import JobStatus, JobState, JobType, JobProgress


class TestContractSchemas:
    """Verifies all shared domain models conform to contract requirements."""

    def test_all_models_have_docstrings(self):
        """Ensure every core schema has an explicit explanatory docstring."""
        models = [
            Project,
            Requirement,
            CodeEntity,
            APIRoute,
            TestCase,
            TestExecution,
            Failure,
            AuditFinding,
            JobStatus,
            APIResponse,
        ]
        for model in models:
            assert model.__doc__ is not None and len(model.__doc__.strip()) > 0, f"Model {model.__name__} missing docstring"

    def test_project_schema(self):
        """Validate Project contract fields and serialization."""
        project = Project(
            name="Test Engine",
            description="Intelligence Engine",
            repository_url="https://github.com/test/engine.git",
            provider=RepoProvider.GITHUB,
            status=ProjectStatus.ACTIVE,
        )
        assert isinstance(project.id, uuid.UUID)
        assert project.name == "Test Engine"
        assert project.status == ProjectStatus.ACTIVE
        assert project.total_files == 0

    def test_test_case_provenance_enum_values(self):
        """CRITICAL: TestCase MUST have mandatory provenance enum with exact 4 values."""
        expected_values = {
            "REQUIREMENT_VERIFIED",
            "SCHEMA_DERIVED",
            "COVERAGE_ONLY",
            "AI_INFERRED",
            "MUTATION_TARGETED",
        }
        actual_values = {p.value for p in TestProvenance}
        assert actual_values == expected_values, f"Provenance values mismatch: {actual_values}"

    def test_test_case_requires_provenance(self):
        """Ensure a TestCase cannot be instantiated without specifying provenance."""
        project_id = uuid.uuid4()

        # Valid instantiation
        tc = TestCase(
            project_id=project_id,
            name="test_valid_auth",
            description="Verify token validation",
            test_type=TestType.API_CONTRACT,
            provenance=TestProvenance.REQUIREMENT_VERIFIED,
            file_path="tests/test_auth.py",
            test_code="def test_valid_auth(): pass",
        )
        assert tc.provenance == TestProvenance.REQUIREMENT_VERIFIED

        # Invalid: missing provenance should raise ValidationError
        with pytest.raises(ValidationError):
            TestCase(
                project_id=project_id,
                name="test_invalid",
                description="Missing provenance",
                test_type=TestType.UNIT,
                file_path="tests/test.py",
                test_code="pass",  # missing provenance field
            )

    def test_requirement_schema(self):
        """Validate Requirement contract fields."""
        req = Requirement(
            project_id=uuid.uuid4(),
            identifier="REQ-001",
            title="User Onboarding",
            description="User can sign up with SSO",
            req_type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.HIGH,
            acceptance_criteria=["SSO button visible", "Callback redirects to dashboard"],
        )
        assert req.status == RequirementStatus.DRAFT
        assert len(req.acceptance_criteria) == 2

    def test_code_entity_schema(self):
        """Validate CodeEntity structure and location."""
        entity = CodeEntity(
            project_id=uuid.uuid4(),
            name="CalculateRisk",
            qualified_name="app.engine.risk.CalculateRisk",
            entity_type=EntityType.FUNCTION,
            language="python",
            location=CodeLocation(file_path="app/engine/risk.py", start_line=10, end_line=35),
            visibility=Visibility.PUBLIC,
            complexity_score=3.2,
        )
        assert entity.entity_type == EntityType.FUNCTION
        assert entity.location.start_line == 10

    def test_api_route_schema(self):
        """Validate APIRoute contract."""
        route = APIRoute(
            project_id=uuid.uuid4(),
            path="/api/v1/users/{id}",
            http_method=HTTPMethod.GET,
            summary="Get User",
            auth_requirement=AuthRequirement.BEARER_TOKEN,
        )
        assert route.http_method == HTTPMethod.GET
        assert route.auth_requirement == AuthRequirement.BEARER_TOKEN

    def test_test_execution_schema(self):
        """Validate TestExecution run schema."""
        execution = TestExecution(
            project_id=uuid.uuid4(),
            triggered_by="CI",
            environment=ExecutionEnvironment.DOCKER_SANDBOX,
            status=ExecutionStatus.PASSED,
            total_tests=10,
            passed_tests=10,
        )
        assert execution.status == ExecutionStatus.PASSED
        assert execution.passed_tests == 10

    def test_failure_schema_and_rca(self):
        """Validate Failure defect record and RootCauseAnalysis."""
        failure = Failure(
            project_id=uuid.uuid4(),
            title="NullPointer in UserService",
            error_message="AttributeError: 'NoneType' object has no attribute 'email'",
            category=FailureCategory.NULL_POINTER_OR_NONE,
            severity=FailureSeverity.MAJOR,
            status=FailureStatus.ROOT_CAUSE_IDENTIFIED,
            root_cause=RootCauseAnalysis(
                summary="User object returned None from DB query without existence check.",
                file_path="app/services/user.py",
                line_number=22,
                explanation="Missing None check before accessing user.email attribute.",
                suggested_fix="if user is None: raise UserNotFoundException()",
                confidence_score=0.99,
            ),
        )
        assert failure.root_cause is not None
        assert failure.root_cause.confidence_score == 0.99

    def test_audit_finding_schema(self):
        """Validate AuditFinding security and compliance contract."""
        finding = AuditFinding(
            project_id=uuid.uuid4(),
            rule_id="CWE-79",
            title="Cross-site scripting in template rendering",
            description="Unescaped HTML injection possible via user nickname parameter.",
            category=AuditCategory.SECURITY_VULNERABILITY,
            severity=AuditSeverity.HIGH,
            standard=ComplianceStandard.CWE,
            standard_reference_id="CWE-79",
            location=CodeLocation(file_path="app/views/profile.py", start_line=18, end_line=19),
            status=AuditStatus.OPEN,
            cvss_score=7.5,
        )
        assert finding.standard == ComplianceStandard.CWE
        assert finding.cvss_score == 7.5

    def test_job_status_schema(self):
        """Validate background JobStatus contract."""
        job = JobStatus(
            job_id="job-12345",
            job_type=JobType.REPO_INGESTION,
            status=JobState.RUNNING,
            progress=JobProgress(
                current_step=50,
                total_steps=100,
                percentage=50.0,
                status_message="Extracting Git commits...",
            ),
        )
        assert job.progress.percentage == 50.0
        assert job.status == JobState.RUNNING
