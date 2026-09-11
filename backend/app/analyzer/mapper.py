"""
CodeSentinel Analyzer: Code-to-Requirement Traceability Mapper.

Establishes confidence-scored traceability linkages between extracted Requirement
objects and AST CodeEntity nodes using multi-tiered heuristic matching:
1. Explicit REQ-ID identifier references in docstrings/comments (High confidence: 1.0)
2. Semantic / name / route similarity (Medium confidence: 0.65 - 0.75)
3. Preserves unmapped requirements for coverage gap visibility.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field
from shared.schemas.code_entity import CodeEntity, EntityType
from shared.schemas.requirement import Requirement


class CodeRequirementLink(BaseModel):
    """Traceability linkage between a Requirement and a CodeEntity."""
    requirement_id: uuid.UUID = Field(..., description="UUID of the linked requirement.")
    requirement_identifier: str = Field(..., description="Business identifier (e.g. 'REQ-AUTH-001').")
    code_entity_id: uuid.UUID = Field(..., description="UUID of the implementing code entity.")
    code_entity_name: str = Field(..., description="Name of the code entity.")
    code_entity_type: str = Field(..., description="Type of the code entity (CLASS, FUNCTION, etc.).")
    file_path: str = Field(..., description="Source file containing the entity.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Numerical confidence score.")
    confidence_level: str = Field(..., description="Categorical confidence: HIGH, MEDIUM, LOW.")
    match_type: str = Field(..., description="Heuristic match strategy.")
    rationale: str = Field(..., description="Explanation of the match decision.")


class TraceabilityMapper:
    """Maps requirements to code entities using multi-tiered heuristics."""

    @classmethod
    def map_requirements_to_code(
        cls,
        requirements: List[Requirement],
        code_entities: List[CodeEntity],
    ) -> Tuple[List[CodeRequirementLink], List[Requirement], List[CodeEntity]]:
        """
        Produce confidence-scored links and update requirements' linked_entity_ids.

        Returns:
            Tuple of (links, unmapped_requirements, unmapped_entities)
        """
        links: List[CodeRequirementLink] = []
        matched_req_ids: set[uuid.UUID] = set()
        matched_entity_ids: set[uuid.UUID] = set()

        # Sort entities so specific methods/functions are tested before general classes/files
        callable_first_entities = sorted(
            code_entities,
            key=lambda e: 0 if e.entity_type in (EntityType.FUNCTION, EntityType.METHOD) else (1 if e.entity_type == EntityType.CLASS else 2),
        )

        for req in requirements:
            req_links: List[CodeRequirementLink] = []
            req_id_lower = req.identifier.lower()
            req_title_tokens = set(re.findall(r"[a-z0-9]+", req.title.lower()))
            req_title_tokens = {
                t for t in req_title_tokens
                if len(t) > 3 and t not in ("requirement", "feature", "system", "user", "allow", "should", "must")
            }

            for entity in callable_first_entities:
                # 1. Tier 1: Explicit REQ-ID Mention in Docstring / Source Code
                doc_and_src = f"{entity.docstring or ''} {entity.source_code or ''}".lower()
                if req_id_lower in doc_and_src:
                    link = CodeRequirementLink(
                        requirement_id=req.id,
                        requirement_identifier=req.identifier,
                        code_entity_id=entity.id,
                        code_entity_name=entity.name,
                        code_entity_type=entity.entity_type.value,
                        file_path=entity.location.file_path,
                        confidence=1.0,
                        confidence_level="HIGH",
                        match_type="EXPLICIT_IDENTIFIER",
                        rationale=f"Explicit reference to '{req.identifier}' found in {entity.name} docstring/source.",
                    )
                    req_links.append(link)
                    matched_req_ids.add(req.id)
                    matched_entity_ids.add(entity.id)
                    continue

                # 2. Tier 2: Name / Keyword Similarity (only if not already matched)
                if not req_links and req_title_tokens:
                    entity_name_tokens = set(re.findall(r"[a-z0-9]+", entity.name.lower()))
                    common_tokens = req_title_tokens.intersection(entity_name_tokens)
                    if common_tokens:
                        overlap_ratio = len(common_tokens) / max(1, len(req_title_tokens))
                        confidence = round(min(0.8, 0.5 + (0.3 * overlap_ratio)), 2)
                        link = CodeRequirementLink(
                            requirement_id=req.id,
                            requirement_identifier=req.identifier,
                            code_entity_id=entity.id,
                            code_entity_name=entity.name,
                            code_entity_type=entity.entity_type.value,
                            file_path=entity.location.file_path,
                            confidence=confidence,
                            confidence_level="MEDIUM",
                            match_type="NAME_SIMILARITY",
                            rationale=f"Semantic token overlap ({', '.join(common_tokens)}) between requirement title and {entity.name}.",
                        )
                        req_links.append(link)
                        matched_req_ids.add(req.id)
                        matched_entity_ids.add(entity.id)

            linked_ids = [l.code_entity_id for l in req_links]
            req.linked_entity_ids = linked_ids
            links.extend(req_links)

        unmapped_requirements = [r for r in requirements if r.id not in matched_req_ids]
        unmapped_entities = [e for e in code_entities if e.id not in matched_entity_ids]

        return links, unmapped_requirements, unmapped_entities
