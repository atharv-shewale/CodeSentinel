"""
CodeSentinel Agents Module: Grounding Verification Engine.

CRITICAL GROUNDING RULE:
Every agent response must cite specific evidence actually returned by RAG/graph retrieval
for that query (e.g. specific file paths, function names, or requirement IDs that appeared
in the retrieved context).

Post-processing inspection verifies at least one concrete citation before returning.
If no citation is present or if no context was available, the response is explicitly
tagged `is_grounded = False` / `ungrounded: True` and logged for audit review.
"""

import re
from typing import List, Optional, Set, Tuple
from app.core.logging import logger
from app.rag.models import RAGContext


class GroundingInspector:
    """Inspects agent responses to ensure empirical evidence citations."""

    @classmethod
    def inspect(
        cls,
        response_text: str,
        rag_context: RAGContext,
        project_id: str,
        question: str,
    ) -> Tuple[bool, List[str], Optional[str]]:
        """
        Verify citations in response against retrieved RAG & Graph context.
        
        Returns:
            (is_grounded, cited_evidence, ungrounded_reason)
        """
        if not response_text:
            reason = "Empty response produced by agent."
            cls._log_ungrounded(project_id, question, reason, response_text)
            return False, [], reason

        # Check if RAG context contained any evidence at all
        candidate_citations: Set[str] = set(rag_context.evidence_citations)
        
        # Also extract any words/tokens from RAG chunk titles, file paths, and identifiers
        for hit in (rag_context.code_results + rag_context.requirement_results + rag_context.test_results + rag_context.finding_results):
            if hit.file_path:
                candidate_citations.add(hit.file_path)
            qname = hit.metadata.get("qualified_name") or hit.metadata.get("name")
            if qname:
                candidate_citations.add(qname)
            ident = hit.metadata.get("identifier")
            if ident:
                candidate_citations.add(ident)
            rule = hit.metadata.get("rule_id")
            if rule:
                candidate_citations.add(rule)

        if not candidate_citations:
            reason = (
                "Zero relevant evidence was retrieved by RAG/Graph for this project query. "
                "The agent cannot produce a grounded answer without empirical codebase artifacts."
            )
            cls._log_ungrounded(project_id, question, reason, response_text)
            return False, [], reason

        # Inspect response text for occurrences of candidate citations
        found_citations: List[str] = []
        resp_lower = response_text.lower()

        for candidate in candidate_citations:
            cand_str = str(candidate).strip()
            if not cand_str:
                continue

            # Check full match or basename match
            cand_lower = cand_str.lower()
            if cand_lower in resp_lower:
                found_citations.append(cand_str)
            elif "/" in cand_str or "\\" in cand_str:
                # Check basename (e.g. auth.py from app/core/auth.py)
                basename = cand_str.replace("\\", "/").split("/")[-1]
                if basename and len(basename) >= 3 and basename.lower() in resp_lower:
                    found_citations.append(cand_str)

        # Remove duplicate citations
        unique_citations = sorted(list(set(found_citations)))

        if not unique_citations:
            reason = (
                f"Agent response failed grounding verification: Response contains no explicit citations "
                f"matching any of the {len(candidate_citations)} retrieved codebase evidence items."
            )
            cls._log_ungrounded(project_id, question, reason, response_text)
            return False, [], reason

        return True, unique_citations, None

    @classmethod
    def _log_ungrounded(cls, project_id: str, question: str, reason: str, response: str) -> None:
        """Log ungrounded response for audit review (do not discard)."""
        logger.warning(
            f"[UNGROUNDED_AGENT_RESPONSE] Project: {project_id} | Question: '{question[:80]}' | "
            f"Reason: {reason} | Response Snippet: '{response[:120]}...'"
        )
