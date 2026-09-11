"""
CodeSentinel Failures Module: Failure Analysis & Root Cause Diagnostic Engine.

Correlates execution test failures with:
- Functions / code entities under test (via Module 2 system model)
- Commit metadata (noting when unavailable without fabrication)
- Prior failure nodes (via Module 3 knowledge graph query: failure_functions)
- Module 3 Failure Agent with mandatory Grounding Rule enforcement:
  ONLY populates RootCauseAnalysis narrative if is_grounded is True.
  If ungrounded, stores raw evidence without speculative narrative.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import uuid
from shared.schemas.common import utc_now
from shared.schemas.failure import (
    Failure,
    FailureCategory,
    FailureSeverity,
    FailureStatus,
    RootCauseAnalysis,
)
from shared.schemas.test_case import TestCase
from shared.schemas.test_execution import ExecutionStatus, TestExecution, TestResultItem
from app.core.logging import logger
from app.failures.store import FailureStore
from app.testing.client import ExternalServiceClient


class FailureAnalyzer:
    """Automated failure diagnostic and root cause analysis engine."""

    def __init__(
        self,
        external_client: Optional[ExternalServiceClient] = None,
        store: Optional[FailureStore] = None,
    ):
        self._client = external_client or ExternalServiceClient()
        self._store = store or FailureStore()

    @staticmethod
    def infer_category(error_message: str, stack_trace: Optional[str]) -> FailureCategory:
        """Categorize failure by inspecting error message and stack trace."""
        text = f"{error_message}\n{stack_trace or ''}".lower()

        if "syntaxerror" in text:
            return FailureCategory.SYNTAX_ERROR
        if "assertionerror" in text or "assert " in text:
            return FailureCategory.ASSERTION_FAILED
        if "timed out" in text or "timeout" in text:
            return FailureCategory.TIMEOUT
        if "attributeerror: 'nonetype'" in text or "nullpointer" in text or "is none" in text:
            return FailureCategory.NULL_POINTER_OR_NONE
        if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
            return FailureCategory.AUTHENTICATION_FAILURE
        if "modulenotfounderror" in text or "importerror" in text or "environment" in text:
            return FailureCategory.ENVIRONMENT_ISSUE
        if "schema" in text or "validation" in text or "422" in text:
            return FailureCategory.SCHEMA_VIOLATION
        if "slow" in text or "latency" in text:
            return FailureCategory.PERFORMANCE_REGRESSION

        return FailureCategory.LOGIC_ERROR

    @staticmethod
    def infer_severity(category: FailureCategory, status: ExecutionStatus) -> FailureSeverity:
        """Determine failure impact severity rating."""
        if status == ExecutionStatus.TIMED_OUT or category == FailureCategory.SYNTAX_ERROR:
            return FailureSeverity.CRITICAL
        if category in (FailureCategory.ENVIRONMENT_ISSUE, FailureCategory.AUTHENTICATION_FAILURE):
            return FailureSeverity.BLOCKER
        if category == FailureCategory.ASSERTION_FAILED:
            return FailureSeverity.MAJOR
        return FailureSeverity.MINOR

    async def analyze_failure(
        self,
        project_id: uuid.UUID,
        result_item: TestResultItem,
        test_case: Optional[TestCase] = None,
        test_execution_id: Optional[uuid.UUID] = None,
        commit_sha: Optional[str] = None,
    ) -> Failure:
        """Perform correlated root cause analysis for a failing or errored test result."""
        # 1. Fetch system model from Module 2 to correlate target entity
        system_model = await self._client.get_system_model(project_id) or {}
        entities = system_model.get("entities") or []

        suspected_entity: Optional[Dict[str, Any]] = None
        if test_case and test_case.target_entity_id:
            for ent in entities:
                if str(ent.get("id")) == str(test_case.target_entity_id):
                    suspected_entity = ent
                    break

        # If not directly linked, attempt to extract function name from error/test name
        if not suspected_entity:
            candidate_name = result_item.test_name.replace("test_", "")
            for ent in entities:
                if ent.get("name") and ent["name"].lower() in candidate_name.lower():
                    suspected_entity = ent
                    break

        # 2. Correlate recent commit metadata (or mark as unavailable without fabrication)
        commit_info = commit_sha if commit_sha else "Unavailable (No commit SHA provided)"

        # 3. Query Module 3 knowledge graph for historical failure nodes
        graph_failures = None
        if suspected_entity and suspected_entity.get("name"):
            graph_failures = await self._client.query_knowledge_graph(
                project_id=project_id,
                query_type="failure_functions",
                target_name=suspected_entity["name"],
            )

        # 4. Infer failure category and severity
        category = self.infer_category(result_item.error_message or "", result_item.stack_trace)
        severity = self.infer_severity(category, result_item.status)

        # 5. Query Module 3 Failure Agent for diagnostic narrative
        agent_context = {
            "test_name": result_item.test_name,
            "error_message": result_item.error_message,
            "stack_trace": result_item.stack_trace,
            "suspected_entity": suspected_entity.get("name") if suspected_entity else None,
            "commit_info": commit_info,
            "prior_failures": graph_failures,
        }

        agent_response = await self._client.ask_agent(
            project_id=project_id,
            agent_type="FAILURE_AGENT",
            question=f"Diagnose root cause for failure in test '{result_item.test_name}': {result_item.error_message}",
            context=agent_context,
        )

        # 6. INVARIANT: Grounding Rule Enforcement
        # ONLY accept narrative if is_grounded == True. If ungrounded, store raw evidence without speculation.
        rca: Optional[RootCauseAnalysis] = None
        if agent_response and isinstance(agent_response, dict):
            is_grounded = agent_response.get("is_grounded", False)
            if is_grounded:
                # Agent output is factually grounded in verifiable AST/execution context
                summary = agent_response.get("summary") or agent_response.get("answer", "Root cause identified.")
                explanation = agent_response.get("explanation") or summary
                suggested_fix = agent_response.get("suggested_fix")
                confidence = float(agent_response.get("confidence_score", 0.85))

                suspected_id = None
                if suspected_entity and suspected_entity.get("id"):
                    try:
                        suspected_id = uuid.UUID(str(suspected_entity["id"]))
                    except (ValueError, TypeError):
                        pass

                rca = RootCauseAnalysis(
                    summary=summary[:256],
                    suspected_entity_id=suspected_id,
                    file_path=suspected_entity.get("file_path") if suspected_entity else None,
                    line_number=suspected_entity.get("start_line") if suspected_entity else None,
                    explanation=explanation,
                    suggested_fix=suggested_fix,
                    confidence_score=min(max(confidence, 0.0), 1.0),
                )
            else:
                logger.info(
                    f"Failure Agent response for test '{result_item.test_name}' was UNGROUNDED. "
                    "Omitting speculative narrative to preserve diagnostic veracity."
                )
                rca = None

        now = utc_now()
        failure = Failure(
            id=uuid.uuid4(),
            project_id=project_id,
            test_execution_id=test_execution_id,
            test_case_id=test_case.id if test_case else result_item.test_case_id,
            title=f"Failure in {result_item.test_name}: {(result_item.error_message or 'Execution failed')[:120]}",
            error_message=result_item.error_message or "Unknown execution error",
            stack_trace=result_item.stack_trace,
            category=category,
            severity=severity,
            status=FailureStatus.ROOT_CAUSE_IDENTIFIED if rca else FailureStatus.DETECTED,
            root_cause=rca,
            occurrences_count=1,
            created_at=now,
            updated_at=now,
            metadata={
                "suspected_entity": suspected_entity.get("name") if suspected_entity else None,
                "commit_sha": commit_info,
                "graph_correlated": bool(graph_failures),
                "is_grounded": bool(agent_response.get("is_grounded", False)) if agent_response else False,
            },
        )

        # 7. Persist Failure domain entity in PostgreSQL
        await self._store.save(failure)

        # 8. Push failure into knowledge graph via Module 3's build mechanism
        try:
            await self._client.trigger_knowledge_graph_build(project_id)
        except Exception as kg_err:
            logger.warning(f"Could not trigger knowledge graph build for project {project_id}: {kg_err}")

        return failure

    async def analyze_execution_run(
        self,
        execution: TestExecution,
        test_cases_map: Optional[Dict[uuid.UUID, TestCase]] = None,
    ) -> List[Failure]:
        """Analyze all failing/errored tests in a complete test execution run."""
        failures: List[Failure] = []
        tc_map = test_cases_map or {}

        for item in execution.results:
            if item.status in (ExecutionStatus.FAILED, ExecutionStatus.ERROR, ExecutionStatus.TIMED_OUT):
                tc = tc_map.get(item.test_case_id)
                f = await self.analyze_failure(
                    project_id=execution.project_id,
                    result_item=item,
                    test_case=tc,
                    test_execution_id=execution.id,
                    commit_sha=execution.commit_sha,
                )
                failures.append(f)

        return failures
