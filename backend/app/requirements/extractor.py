"""
CodeSentinel Requirements Module: Specification Document Parser & Requirement Extractor.

Extracts structured Requirement objects from Markdown/text, PDF, and DOCX files.
Enforces the STRICT ground-truth rule: acceptance criteria are ONLY populated if
explicitly stated in the source text (e.g., under 'Acceptance Criteria', Given/When/Then,
or explicit numbered criteria). Never guesses, paraphrases, or invents acceptance criteria.
"""

from __future__ import annotations

import io
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
import pypdf
import docx
from shared.schemas.common import utc_now
from shared.schemas.requirement import (
    Requirement,
    RequirementPriority,
    RequirementStatus,
    RequirementType,
)


class DocumentParsingError(Exception):
    """Raised when document content is unreadable or malformed."""
    def __init__(self, message: str, code: str = "DOCUMENT_PARSE_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code


class DocumentReader:
    """Extracts raw text from PDF, DOCX, and text/markdown files."""

    @classmethod
    def read_document_text(cls, file_content: bytes, filename: str) -> str:
        """Extract text based on file extension."""
        ext = os.path.splitext(filename)[1].lower()

        if ext in (".txt", ".md", ".markdown", ".rst"):
            try:
                return file_content.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return file_content.decode("latin-1")
                except Exception as e:
                    raise DocumentParsingError(f"Failed to decode text document: {str(e)}", code="TEXT_DECODE_ERROR")

        elif ext == ".pdf":
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_content))
                pages = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        pages.append(text)
                if not pages:
                    raise DocumentParsingError("PDF contains no extractable text.", code="PDF_EMPTY")
                return "\n\n".join(pages)
            except Exception as e:
                raise DocumentParsingError(f"Failed to parse PDF document: {str(e)}", code="PDF_PARSE_ERROR")

        elif ext in (".docx", ".doc"):
            try:
                doc = docx.Document(io.BytesIO(file_content))
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                return "\n".join(paragraphs)
            except Exception as e:
                raise DocumentParsingError(f"Failed to parse DOCX document: {str(e)}", code="DOCX_PARSE_ERROR")

        else:
            raise DocumentParsingError(f"Unsupported document format '{ext}'. Supported: .md, .txt, .pdf, .docx", code="UNSUPPORTED_FORMAT")


class RequirementExtractor:
    """Extracts strictly-validated Requirement domain objects from document text."""

    @classmethod
    def extract_from_text(
        cls,
        text: str,
        project_id: uuid.UUID,
        source_name: str = "document",
    ) -> List[Requirement]:
        """
        Parse requirements from text.
        Maintains strict boundary: if no explicit acceptance criteria exist, criteria list remains empty.
        """
        if not text or not text.strip():
            return []

        requirements: List[Requirement] = []
        sections = cls._split_into_sections(text)

        if sections:
            for idx, (header, body) in enumerate(sections, start=1):
                req = cls._parse_section(header, body, project_id, idx, source_name)
                if req:
                    requirements.append(req)

        # Fallback if no sections parsed
        if not requirements:
            single_req = cls._parse_unstructured_text(text, project_id, source_name)
            requirements.append(single_req)

        return requirements

    @classmethod
    def _split_into_sections(cls, text: str) -> List[Tuple[str, str]]:
        """Split document by requirement headers (ignoring subheadings like '### Acceptance Criteria')."""
        lines = text.splitlines()
        sections: List[Tuple[str, List[str]]] = []
        current_header = ""
        current_body: List[str] = []

        subheading_filter = re.compile(
            r"^#{1,6}\s*(?:Acceptance Criteria|Criteria|Description|Notes|Details|Scenarios|Examples|Verification)\b",
            re.IGNORECASE,
        )

        req_header_pattern = re.compile(
            r"^(?:#{1,3}\s+)?(?:(REQ-[A-Z0-9_\-]+|Requirement\s+\d+|Feature:\s+.*|User Story\s+\d+:?|User Story:.*|UC-\d+:?).*|#{1,2}\s+(?!Software Requirements Specification|SRS\b).*)",
            re.IGNORECASE,
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_body.append(line)
                continue

            # Sub-headings like ### Acceptance Criteria belong to the current section
            if subheading_filter.match(stripped):
                current_body.append(line)
                continue

            # Check if this line is a new requirement header
            if req_header_pattern.match(stripped):
                # Ignore top-level document title headers without requirement info
                if stripped.lower().startswith(("# software requirements", "# srs", "# product backlog")):
                    continue

                if current_header:
                    sections.append((current_header, "\n".join(current_body)))
                    current_body = []
                current_header = stripped.lstrip("#").strip()
            else:
                current_body.append(line)

        if current_header:
            sections.append((current_header, "\n".join(current_body)))

        return [(h, b) for h, b in sections if h.strip() or b.strip()]

    @classmethod
    def _parse_section(
        cls,
        header: str,
        body: str,
        project_id: uuid.UUID,
        index: int,
        source_name: str,
    ) -> Optional[Requirement]:
        """Parse a structured requirement section."""
        now = utc_now()
        full_text = f"{header}\n{body}".strip()

        # Skip document title or empty header sections
        if not header.strip() and not body.strip():
            return None
        if header.lower().startswith(("software requirements", "srs", "product backlog", "table of contents")):
            return None

        # 1. Identifier Extraction (e.g., REQ-AUTH-001 or generated)
        id_match = re.search(r"\b(REQ-[A-Z0-9_\-]+|US-\d+|UC-\d+)\b", header, re.IGNORECASE)
        if not id_match:
            id_match = re.search(r"\b(REQ-[A-Z0-9_\-]+|US-\d+|UC-\d+)\b", body, re.IGNORECASE)

        identifier = id_match.group(1).upper() if id_match else f"REQ-DOC-{index:03d}"

        # 2. Title Extraction
        clean_title = re.sub(
            r"^(?:REQ-[A-Z0-9_\-]+|Requirement\s+\d+|Feature:|User Story\s+\d+:?|User Story:)\s*[:-]?\s*",
            "",
            header,
            flags=re.IGNORECASE,
        ).strip()
        if not clean_title:
            clean_title = f"Requirement {identifier}"

        # 3. Acceptance Criteria Extraction (STRICT: only explicit criteria)
        acceptance_criteria = cls._extract_explicit_acceptance_criteria(body)

        # 4. Priority & Type Classification
        priority = RequirementPriority.MEDIUM
        if re.search(r"\b(critical|blocker|p0)\b", full_text, re.IGNORECASE):
            priority = RequirementPriority.CRITICAL
        elif re.search(r"\b(high priority|p1|urgent)\b", full_text, re.IGNORECASE):
            priority = RequirementPriority.HIGH
        elif re.search(r"\b(low priority|p3|nice to have)\b", full_text, re.IGNORECASE):
            priority = RequirementPriority.LOW

        req_type = RequirementType.FUNCTIONAL
        if re.search(r"\b(security|authentication|authorization|encryption|rbac|jwt)\b", full_text, re.IGNORECASE):
            req_type = RequirementType.SECURITY
        elif re.search(r"\b(performance|latency|throughput|sla|response time)\b", full_text, re.IGNORECASE):
            req_type = RequirementType.PERFORMANCE
        elif re.search(r"\b(compliance|gdpr|hipaa|audit)\b", full_text, re.IGNORECASE):
            req_type = RequirementType.COMPLIANCE

        return Requirement(
            id=uuid.uuid4(),
            project_id=project_id,
            identifier=identifier,
            title=clean_title[:256],
            description=body.strip() or clean_title,
            req_type=req_type,
            priority=priority,
            status=RequirementStatus.APPROVED if acceptance_criteria else RequirementStatus.DRAFT,
            acceptance_criteria=acceptance_criteria,
            created_at=now,
            updated_at=now,
            metadata={"source": source_name, "raw_header": header},
        )

    @classmethod
    def _extract_explicit_acceptance_criteria(cls, body: str) -> List[str]:
        """
        STRICT CRITERIA EXTRACTOR:
        Only extracts criteria if explicitly labeled under 'Acceptance Criteria',
        'Given/When/Then' Gherkin scenarios, or explicit numbered verification clauses.
        Returns empty list if none are explicitly declared.
        """
        criteria: List[str] = []
        lines = body.splitlines()

        in_ac_block = False
        for line in lines:
            stripped = line.strip()
            # Check for header
            if re.match(r"^#{1,6}\s*Acceptance Criteria|^Acceptance Criteria\s*:", stripped, re.IGNORECASE):
                in_ac_block = True
                continue

            if in_ac_block:
                if stripped.startswith("#") and not re.match(r"^#{1,6}\s*Acceptance Criteria", stripped, re.IGNORECASE):
                    in_ac_block = False
                    continue

                bullet_match = re.match(r"^(?:[\*\-\+]|\d+\.)\s+(.+)$", stripped)
                if bullet_match:
                    criteria.append(bullet_match.group(1).strip())
                elif stripped.lower().startswith(("given ", "when ", "then ", "and ", "shall ", "must ")):
                    criteria.append(stripped)

        if criteria:
            return [c for c in criteria if len(c) > 3]

        # Look for Gherkin Given/When/Then scenarios anywhere in the body
        gherkin_lines = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"^(?:Given|When|Then|And|But)\s+.+", stripped, re.IGNORECASE):
                gherkin_lines.append(stripped)

        if gherkin_lines:
            return gherkin_lines

        return []

    @classmethod
    def _parse_unstructured_text(
        cls,
        text: str,
        project_id: uuid.UUID,
        source_name: str,
    ) -> Requirement:
        """Handle loosely-written or unstructured document as a single requirement with empty criteria."""
        now = utc_now()
        first_line = text.strip().splitlines()[0] if text.strip() else "Unstructured Specification"
        title = first_line.lstrip("#").strip()[:100]

        criteria = cls._extract_explicit_acceptance_criteria(text)

        return Requirement(
            id=uuid.uuid4(),
            project_id=project_id,
            identifier="REQ-DOC-001",
            title=title or "General System Requirement",
            description=text.strip(),
            req_type=RequirementType.FUNCTIONAL,
            priority=RequirementPriority.MEDIUM,
            status=RequirementStatus.APPROVED if criteria else RequirementStatus.DRAFT,
            acceptance_criteria=criteria,
            created_at=now,
            updated_at=now,
            metadata={
                "source": source_name,
                "note": "Extracted from unstructured specification; acceptance criteria kept strictly explicit.",
            },
        )
