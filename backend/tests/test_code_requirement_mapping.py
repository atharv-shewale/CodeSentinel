"""
CodeSentinel Traceability Mapping Test Suite.

Tests confidence-scored linkages between Requirement entities and CodeEntity nodes,
including explicit REQ-ID tags, name similarity, and unmapped coverage gap retention.
"""

import uuid
import pytest
from shared.schemas.code_entity import (
    CodeEntity,
    CodeLocation,
    EntityType,
    Visibility,
)
from shared.schemas.common import utc_now
from shared.schemas.requirement import Requirement, RequirementStatus
from app.analyzer.mapper import TraceabilityMapper
from app.analyzer.python_analyzer import PythonCodeAnalyzer
from tests.fixtures.analysis.sample_sources import SAMPLE_PYTHON_SOURCE
from tests.fixtures.requirements.sample_documents import STRUCTURED_SRS_MARKDOWN


class TestCodeRequirementMapping:
    """Verifies heuristic mapping precision and confidence calibration."""

    def test_explicit_req_id_high_confidence_link(self):
        """
        TEST #9: A case with an explicit REQ-ID comment in code ->
        assert high-confidence link (confidence 1.0, label HIGH).
        """
        project_id = uuid.uuid4()
        now = utc_now()

        # Requirement
        req_auth = Requirement(
            id=uuid.uuid4(),
            project_id=project_id,
            identifier="REQ-AUTH-001",
            title="User Authentication",
            description="Authenticate users with password hashing.",
            acceptance_criteria=["Return token on valid login"],
            status=RequirementStatus.APPROVED,
        )

        # Code Entities extracted from Python source with "Requirement: REQ-AUTH-001"
        entities = PythonCodeAnalyzer.analyze_file(
            file_path="app/auth.py",
            source_code=SAMPLE_PYTHON_SOURCE,
            project_id=project_id,
        )

        links, unmapped_reqs, unmapped_ents = TraceabilityMapper.map_requirements_to_code(
            requirements=[req_auth],
            code_entities=entities,
        )

        assert len(links) >= 1
        auth_link = next(l for l in links if l.requirement_identifier == "REQ-AUTH-001")
        assert auth_link.confidence == 1.0
        assert auth_link.confidence_level == "HIGH"
        assert auth_link.match_type == "EXPLICIT_IDENTIFIER"
        assert "authenticate_user" in auth_link.code_entity_name
        assert len(unmapped_reqs) == 0

    def test_name_similarity_medium_confidence_link(self):
        """
        TEST #10: A case with only name-similarity match ->
        assert medium-confidence link, not treated as certain.
        """
        project_id = uuid.uuid4()
        now = utc_now()

        # Requirement without explicit REQ-ID match in code
        req_payment = Requirement(
            id=uuid.uuid4(),
            project_id=project_id,
            identifier="REQ-PAY-999",
            title="Process Billing Payment Transaction",
            description="Handle credit card billing transactions.",
        )

        # Code entity without REQ-PAY-999 tag, but with matching name
        payment_entity = CodeEntity(
            id=uuid.uuid4(),
            project_id=project_id,
            name="process_payment_transaction",
            qualified_name="app.billing.process_payment_transaction",
            entity_type=EntityType.FUNCTION,
            language="python",
            location=CodeLocation(file_path="app/billing.py", start_line=10, end_line=25),
            docstring="Executes payment charge against payment gateway.",
            created_at=now,
            updated_at=now,
        )

        links, unmapped_reqs, unmapped_ents = TraceabilityMapper.map_requirements_to_code(
            requirements=[req_payment],
            code_entities=[payment_entity],
        )

        assert len(links) == 1
        link = links[0]
        assert link.confidence < 1.0
        assert link.confidence_level == "MEDIUM"
        assert link.match_type == "NAME_SIMILARITY"

    def test_unmapped_requirement_retained_in_coverage_gap(self):
        """
        TEST #11: A requirement with no plausible code match ->
        assert it appears as unmapped in the system model, not silently dropped.
        """
        project_id = uuid.uuid4()
        now = utc_now()

        # Requirement with no matching code
        unimplemented_req = Requirement(
            id=uuid.uuid4(),
            project_id=project_id,
            identifier="REQ-AUDIT-404",
            title="Export Blockchain Audit Logs",
            description="Archive all ledger transactions to cold storage.",
        )

        # Unrelated code entity
        unrelated_entity = CodeEntity(
            id=uuid.uuid4(),
            project_id=project_id,
            name="render_header_icon",
            qualified_name="ui.components.render_header_icon",
            entity_type=EntityType.FUNCTION,
            language="typescript",
            location=CodeLocation(file_path="ui/header.tsx", start_line=1, end_line=5),
            created_at=now,
            updated_at=now,
        )

        links, unmapped_reqs, unmapped_ents = TraceabilityMapper.map_requirements_to_code(
            requirements=[unimplemented_req],
            code_entities=[unrelated_entity],
        )

        assert len(links) == 0
        assert len(unmapped_reqs) == 1
        assert unmapped_reqs[0].identifier == "REQ-AUDIT-404"
        assert len(unmapped_ents) == 1
