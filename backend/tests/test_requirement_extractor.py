"""
CodeSentinel Requirements Test Suite: Document Parsing & Strict Criteria Enforcement.

Tests extraction from structured SRS, loose user stories, ambiguous documents,
and corrupt document error handling.
"""

import uuid
import pytest
from shared.schemas.requirement import Requirement, RequirementStatus
from app.requirements.extractor import (
    DocumentParsingError,
    DocumentReader,
    RequirementExtractor,
)
from tests.fixtures.requirements.sample_documents import (
    AMBIGUOUS_PROSE_DOCUMENT,
    LOOSE_USER_STORY_MARKDOWN,
    STRUCTURED_SRS_MARKDOWN,
)


class TestRequirementExtractor:
    """Verifies requirement parsing fidelity and the strict no-invention rule for acceptance criteria."""

    def test_structured_srs_document_extraction(self):
        """
        TEST #5: A well-structured SRS-style document with explicit acceptance criteria ->
        assert exact criteria extracted, matching the source text's intent.
        """
        project_id = uuid.uuid4()
        reqs = RequirementExtractor.extract_from_text(
            text=STRUCTURED_SRS_MARKDOWN,
            project_id=project_id,
            source_name="srs.md",
        )

        assert len(reqs) == 2

        # 1. Check REQ-AUTH-001
        auth_req = next(r for r in reqs if r.identifier == "REQ-AUTH-001")
        assert "User Authentication" in auth_req.title
        assert len(auth_req.acceptance_criteria) == 3
        assert any("valid session token" in c for c in auth_req.acceptance_criteria)
        assert any("401" in c or "None" in c for c in auth_req.acceptance_criteria)
        assert auth_req.status == RequirementStatus.APPROVED

        # 2. Check REQ-SEC-002
        sec_req = next(r for r in reqs if r.identifier == "REQ-SEC-002")
        assert "Password Hashing" in sec_req.title
        assert len(sec_req.acceptance_criteria) == 2
        assert any("salted hash" in c for c in sec_req.acceptance_criteria)
        assert sec_req.status == RequirementStatus.APPROVED

        # All entities must strictly validate as Pydantic models
        for r in reqs:
            assert isinstance(r, Requirement)
            assert r.project_id == project_id

    def test_loose_user_story_leaves_criteria_strictly_empty(self):
        """
        TEST #6: A loosely-written user-story document with NO explicit criteria ->
        assert acceptance_criteria is empty, NOT invented.
        """
        project_id = uuid.uuid4()
        reqs = RequirementExtractor.extract_from_text(
            text=LOOSE_USER_STORY_MARKDOWN,
            project_id=project_id,
            source_name="backlog.md",
        )

        assert len(reqs) >= 2
        for req in reqs:
            # STRICT RULE: Must NOT invent criteria
            assert req.acceptance_criteria == [], (
                f"VIOLATION: Criteria were fabricated for {req.identifier} ({req.acceptance_criteria})"
            )
            assert req.status == RequirementStatus.DRAFT

    def test_ambiguous_prose_document_extraction(self):
        """
        TEST #7: A deliberately ambiguous document (vague prose, no headers, no Gherkin) ->
        assert the strict 'leave empty rather than invent' rule holds.
        """
        project_id = uuid.uuid4()
        reqs = RequirementExtractor.extract_from_text(
            text=AMBIGUOUS_PROSE_DOCUMENT,
            project_id=project_id,
            source_name="notes.txt",
        )

        assert len(reqs) == 1
        req = reqs[0]
        # Must produce valid requirement without failing, but with zero fabricated criteria
        assert isinstance(req, Requirement)
        assert req.acceptance_criteria == []
        assert "brainstorming" in req.description.lower()

    def test_corrupt_unreadable_document_typed_error(self):
        """
        TEST #8: A corrupt/unreadable document upload ->
        assert a clean typed DocumentParsingError is raised, not a raw crash.
        """
        corrupt_bytes = b"NOT_A_VALID_PDF_HEADER_OR_DOCX"

        with pytest.raises(DocumentParsingError) as exc_info:
            DocumentReader.read_document_text(corrupt_bytes, "specification.pdf")

        assert exc_info.value.code in ("PDF_PARSE_ERROR", "PDF_EMPTY")
        assert "pdf" in exc_info.value.message.lower()

    def test_unsupported_format_raises_typed_error(self):
        """Verify unsupported file extension raises typed error."""
        with pytest.raises(DocumentParsingError) as exc_info:
            DocumentReader.read_document_text(b"some content", "specs.exe")

        assert exc_info.value.code == "UNSUPPORTED_FORMAT"
