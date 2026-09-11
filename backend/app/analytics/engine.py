"""
CodeSentinel Analytics Module: Engineering Intelligence Engine.

Computes 100% deterministic metrics:
1. Test pass rate: overall and broken down by provenance tier (REQUIREMENT_VERIFIED, SCHEMA_DERIVED, COVERAGE_ONLY, AI_INFERRED).
2. Coverage snapshot and language breakdown.
3. Failure trends and recurring failure clusters by target function/module.
4. Security and code-quality findings distribution by severity.
5. Transparent project health score formula:
   HealthScore = 0.35 * ReqCoverage + 0.25 * ReqPassRate + 0.15 * QualityScore + 0.15 * SecurityScore + 0.10 * ArchitectureScore
6. Requirement -> Module -> Code -> Test -> Execution -> Result Traceability Matrix.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from shared.schemas.audit import AuditCategory, AuditSeverity
from shared.schemas.test_case import TestProvenance
from shared.schemas.test_execution import ExecutionStatus
from app.audits.client import AuditExternalClient
from app.audits.store import AuditFindingStore
from app.core.logging import logger


class AnalyticsEngine:
    """Computes transparent, deterministic engineering intelligence metrics."""

    def __init__(
        self,
        client: Optional[AuditExternalClient] = None,
        audit_store: Optional[AuditFindingStore] = None,
    ):
        self.client = client or AuditExternalClient()
        self.audit_store = audit_store or AuditFindingStore()

    # --------------------------------------------------------------------------
    # Health Score Calculation Formula
    # --------------------------------------------------------------------------
    @staticmethod
    def calculate_health_score(
        req_coverage_pct: float,
        req_pass_rate_pct: float,
        critical_vulns: int = 0,
        high_vulns: int = 0,
        medium_vulns: int = 0,
        high_cc_count: int = 0,
        duplication_count: int = 0,
        smell_count: int = 0,
        circular_dep_count: int = 0,
        layer_violation_count: int = 0,
        req_coverage_evaluated: bool = True,
        req_pass_rate_evaluated: bool = True,
        quality_evaluated: bool = True,
        security_evaluated: bool = True,
        architecture_evaluated: bool = True,
    ) -> Dict[str, Any]:
        """
        Documented, Transparent Project Health Score Formula:

        HealthScore = (
            0.35 * RequirementCoverageScore +
            0.25 * RequirementPassRateScore +
            0.15 * CodeQualityScore +
            0.15 * SecurityScore +
            0.10 * ArchitectureScore
        )

        Component Definitions:
        - RequirementCoverageScore: % of requirements with >= 1 verification test [0..100].
        - RequirementPassRateScore: pass rate % of requirement-verified tests [0..100].
        - CodeQualityScore: max(0, 100 - (high_cc * 10 + duplications * 5 + smells * 2)).
        - SecurityScore: max(0, 100 - (critical_vulns * 25 + high_vulns * 15 + medium_vulns * 5)).
        - ArchitectureScore: max(0, 100 - (circular_deps * 25 + layer_violations * 15)).

        Unevaluated components score 0.0 with evaluated=False (per Fix 5).
        """
        # 1. Coverage Component (35%)
        if req_coverage_evaluated:
            c_req_coverage = max(0.0, min(100.0, float(req_coverage_pct)))
        else:
            c_req_coverage = 0.0

        # 2. Pass Rate Component (25%)
        if req_pass_rate_evaluated:
            c_req_pass_rate = max(0.0, min(100.0, float(req_pass_rate_pct)))
        else:
            c_req_pass_rate = 0.0

        # 3. Quality Component (15%)
        if quality_evaluated:
            quality_penalty = (high_cc_count * 10) + (duplication_count * 5) + (smell_count * 2)
            c_quality = max(0.0, 100.0 - float(quality_penalty))
        else:
            quality_penalty = 0
            c_quality = 0.0

        # 4. Security Component (15%)
        if security_evaluated:
            security_penalty = (critical_vulns * 25) + (high_vulns * 15) + (medium_vulns * 5)
            c_security = max(0.0, 100.0 - float(security_penalty))
        else:
            security_penalty = 0
            c_security = 0.0

        # 5. Architecture Component (10%)
        if architecture_evaluated:
            arch_penalty = (circular_dep_count * 25) + (layer_violation_count * 15)
            c_arch = max(0.0, 100.0 - float(arch_penalty))
        else:
            arch_penalty = 0
            c_arch = 0.0

        final_score = (
            0.35 * c_req_coverage
            + 0.25 * c_req_pass_rate
            + 0.15 * c_quality
            + 0.15 * c_security
            + 0.10 * c_arch
        )

        any_evaluated = any([
            req_coverage_evaluated,
            req_pass_rate_evaluated,
            quality_evaluated,
            security_evaluated,
            architecture_evaluated,
        ])

        if not any_evaluated:
            grade = "Not yet evaluated"
        else:
            grade = (
                "A" if final_score >= 90
                else "B" if final_score >= 80
                else "C" if final_score >= 70
                else "D" if final_score >= 60
                else "F"
            )

        return {
            "health_score": round(final_score, 1),
            "grade": grade,
            "evaluated": any_evaluated,
            "formula": "0.35 * ReqCoverage + 0.25 * ReqPassRate + 0.15 * Quality + 0.15 * Security + 0.10 * Architecture",
            "components": {
                "requirement_coverage": {
                    "weight": 0.35,
                    "score": round(c_req_coverage, 1),
                    "evaluated": req_coverage_evaluated,
                },
                "requirement_pass_rate": {
                    "weight": 0.25,
                    "score": round(c_req_pass_rate, 1),
                    "evaluated": req_pass_rate_evaluated,
                },
                "code_quality": {
                    "weight": 0.15,
                    "score": round(c_quality, 1),
                    "penalty": quality_penalty,
                    "evaluated": quality_evaluated,
                },
                "security": {
                    "weight": 0.15,
                    "score": round(c_security, 1),
                    "penalty": security_penalty,
                    "evaluated": security_evaluated,
                },
                "architecture": {
                    "weight": 0.10,
                    "score": round(c_arch, 1),
                    "penalty": arch_penalty,
                    "evaluated": architecture_evaluated,
                },
            },
        }

    # --------------------------------------------------------------------------
    # Tiered Pass Rate Breakdown
    # --------------------------------------------------------------------------
    @staticmethod
    def compute_tiered_pass_rates(
        test_cases: List[Dict[str, Any]],
        executions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compute test execution pass rates:
        - Overall pass rate.
        - Broken down by provenance tier (REQUIREMENT_VERIFIED, SCHEMA_DERIVED, COVERAGE_ONLY, AI_INFERRED).
        """
        # Map test_case_id -> provenance
        tc_provenance_map: Dict[str, str] = {}
        for tc in test_cases:
            tc_id = str(tc.get("id"))
            prov = tc.get("provenance", "UNKNOWN")
            tc_provenance_map[tc_id] = prov

        tier_counts = {
            "REQUIREMENT_VERIFIED": {"total": 0, "passed": 0, "failed": 0, "error": 0},
            "SCHEMA_DERIVED": {"total": 0, "passed": 0, "failed": 0, "error": 0},
            "COVERAGE_ONLY": {"total": 0, "passed": 0, "failed": 0, "error": 0},
            "AI_INFERRED": {"total": 0, "passed": 0, "failed": 0, "error": 0},
        }

        total_execs = 0
        total_passed = 0

        for exc in executions:
            results = exc.get("results") or []
            for item in results:
                tc_id = str(item.get("test_case_id"))
                status = item.get("status")
                prov = tc_provenance_map.get(tc_id, "REQUIREMENT_VERIFIED")

                if prov not in tier_counts:
                    tier_counts[prov] = {"total": 0, "passed": 0, "failed": 0, "error": 0}

                tier_counts[prov]["total"] += 1
                total_execs += 1

                if status == ExecutionStatus.PASSED.value or status == "PASSED":
                    tier_counts[prov]["passed"] += 1
                    total_passed += 1
                elif status == ExecutionStatus.FAILED.value or status == "FAILED":
                    tier_counts[prov]["failed"] += 1
                else:
                    tier_counts[prov]["error"] += 1

        tiered_breakdown = {}
        for tier, stats in tier_counts.items():
            tot = stats["total"]
            pass_pct = round((stats["passed"] / tot * 100.0), 2) if tot > 0 else 0.0
            tiered_breakdown[tier] = {
                "total_runs": tot,
                "passed": stats["passed"],
                "failed": stats["failed"],
                "errors": stats["error"],
                "pass_rate_pct": pass_pct,
            }

        overall_pct = round((total_passed / total_execs * 100.0), 2) if total_execs > 0 else 0.0

        return {
            "overall_pass_rate_pct": overall_pct,
            "total_executions": total_execs,
            "total_passed": total_passed,
            "by_provenance": tiered_breakdown,
        }

    # --------------------------------------------------------------------------
    # Traceability Matrix Assembly
    # --------------------------------------------------------------------------
    @staticmethod
    def build_traceability_matrix(
        requirements: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        test_cases: List[Dict[str, Any]],
        executions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Joins:
        Requirement -> Module -> Code Entity -> Test Case -> Test Execution -> Result Status.
        """
        entity_map = {str(e.get("id")): e for e in entities}
        req_map = {str(r.get("id")): r for r in requirements}

        # Map test_case_id -> latest execution status
        latest_results: Dict[str, Dict[str, Any]] = {}
        for exc in executions:
            results = exc.get("results") or []
            for item in results:
                tc_id = str(item.get("test_case_id"))
                latest_results[tc_id] = {
                    "status": item.get("status", "NOT_RUN"),
                    "duration_ms": item.get("duration_ms", 0.0),
                    "execution_id": exc.get("id"),
                    "executed_at": exc.get("created_at"),
                }

        matrix: List[Dict[str, Any]] = []

        # 1. Join for tests linked to requirements
        for tc in test_cases:
            tc_id = str(tc.get("id"))
            req_id = str(tc.get("requirement_id")) if tc.get("requirement_id") else None
            entity_id = str(tc.get("target_entity_id")) if tc.get("target_entity_id") else None

            req = req_map.get(req_id, {}) if req_id else {}
            entity = entity_map.get(entity_id, {}) if entity_id else {}
            exec_info = latest_results.get(tc_id, {"status": "NOT_RUN", "duration_ms": 0.0})

            matrix.append({
                "requirement_id": req_id,
                "requirement_identifier": req.get("identifier", "N/A"),
                "requirement_title": req.get("title", "Ad-hoc / Unlinked Specification"),
                "module": entity.get("file_path", "unknown").split("/")[0] if entity.get("file_path") else "global",
                "entity_name": entity.get("name", tc.get("file_path", "unlinked")),
                "entity_file_path": entity.get("file_path", tc.get("file_path")),
                "test_case_id": tc_id,
                "test_name": tc.get("name"),
                "provenance": tc.get("provenance", TestProvenance.AI_INFERRED.value),
                "execution_status": exec_info["status"],
                "duration_ms": exec_info["duration_ms"],
            })

        # 2. Include uncovered requirements with no tests
        covered_req_ids = {str(tc.get("requirement_id")) for tc in test_cases if tc.get("requirement_id")}
        for req in requirements:
            r_id = str(req.get("id"))
            if r_id not in covered_req_ids:
                matrix.append({
                    "requirement_id": r_id,
                    "requirement_identifier": req.get("identifier", "REQ-GAP"),
                    "requirement_title": req.get("title", "Requirement"),
                    "module": "N/A",
                    "entity_name": "None",
                    "entity_file_path": "None",
                    "test_case_id": None,
                    "test_name": "UNTESTED_GAP",
                    "provenance": "NONE",
                    "execution_status": "UNTESTED",
                    "duration_ms": 0.0,
                })

        return matrix

    # --------------------------------------------------------------------------
    # Full Analytics Payload Assembly
    # --------------------------------------------------------------------------
    async def get_project_analytics(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Assemble comprehensive intelligence analytics for a project."""
        system_model = await self.client.get_system_model(project_id) or {}
        requirements = system_model.get("requirements", [])
        routes = system_model.get("routes") or system_model.get("apis", [])
        raw_entities = system_model.get("entities") or (system_model.get("functions", []) + system_model.get("classes", []))
        entities = [
            e.model_dump() if hasattr(e, "model_dump") else e
            for e in raw_entities
        ]
        test_cases = await self.client.get_tests(project_id)
        executions = await self.client.get_executions(project_id)
        findings = await self.audit_store.list_for_project(project_id)
        audits_evaluated = len(findings) > 0
        if not audits_evaluated:
            try:
                from app.core.redis import get_redis
                r = await get_redis()
                if await r.get(f"audit:scanned:{project_id}"):
                    audits_evaluated = True
            except Exception:
                pass
            if not audits_evaluated:
                try:
                    from app.core.project_store import ProjectStore
                    p_store = ProjectStore()
                    proj = await p_store.get_project(project_id)
                    if proj and (proj.metadata or {}).get("audits_completed"):
                        audits_evaluated = True
                except Exception:
                    pass

        # 1. Tiered Pass Rates
        pass_rates = self.compute_tiered_pass_rates(test_cases, executions)
        rv_stats = pass_rates["by_provenance"].get("REQUIREMENT_VERIFIED", {})
        if rv_stats.get("total_runs", 0) > 0:
            req_pass_rate = rv_stats.get("pass_rate_pct", 0.0)
            req_pass_rate_evaluated = True
        else:
            # FIX 5: Zero runs must NOT fallback to overall_pass_rate_pct. Treat as not evaluated -> score 0.0.
            req_pass_rate = 0.0
            req_pass_rate_evaluated = False

        # 2. Coverage Metrics
        req_covered_ids = {str(tc.get("requirement_id")) for tc in test_cases if tc.get("provenance") == "REQUIREMENT_VERIFIED" and tc.get("requirement_id")}
        req_cov_pct = round((len(req_covered_ids) / len(requirements) * 100.0), 2) if requirements else 0.0
        req_coverage_evaluated = len(requirements) > 0

        # Per language code coverage
        python_ents = [e for e in entities if str(e.get("file_path", "")).endswith(".py")]
        js_ents = [e for e in entities if any(str(e.get("file_path", "")).endswith(ext) for ext in [".js", ".ts", ".jsx", ".tsx"])]
        tested_ents = {str(tc.get("target_entity_id")) for tc in test_cases if tc.get("target_entity_id")}

        lang_coverage = {}
        if python_ents:
            lang_coverage["Python"] = round((sum(1 for e in python_ents if str(e.get("id")) in tested_ents) / len(python_ents) * 100.0), 2)
        if js_ents:
            lang_coverage["JavaScript/TypeScript"] = round((sum(1 for e in js_ents if str(e.get("id")) in tested_ents) / len(js_ents) * 100.0), 2)

        # 3. Findings breakdown by severity
        severity_counts = {
            "CRITICAL": sum(1 for f in findings if f.severity == AuditSeverity.CRITICAL),
            "HIGH": sum(1 for f in findings if f.severity == AuditSeverity.HIGH),
            "MEDIUM": sum(1 for f in findings if f.severity == AuditSeverity.MEDIUM),
            "LOW": sum(1 for f in findings if f.severity == AuditSeverity.LOW),
        }

        high_cc = sum(1 for f in findings if f.rule_id == "QUAL-COMPLEXITY-HIGH")
        duplications = sum(1 for f in findings if f.rule_id == "QUAL-DUPLICATION-DETECTED")
        smells = sum(1 for f in findings if f.category == AuditCategory.CODE_SMELL and f.rule_id not in ("QUAL-COMPLEXITY-HIGH", "QUAL-DUPLICATION-DETECTED"))
        circular_deps = sum(1 for f in findings if f.rule_id == "ARCH-CIRCULAR-DEPENDENCY")
        layer_violations = sum(1 for f in findings if f.rule_id == "ARCH-LAYER-VIOLATION")

        # 4. Health Score
        health = self.calculate_health_score(
            req_coverage_pct=req_cov_pct,
            req_pass_rate_pct=req_pass_rate,
            critical_vulns=severity_counts["CRITICAL"],
            high_vulns=severity_counts["HIGH"],
            medium_vulns=severity_counts["MEDIUM"],
            high_cc_count=high_cc,
            duplication_count=duplications,
            smell_count=smells,
            circular_dep_count=circular_deps,
            layer_violation_count=layer_violations,
            req_coverage_evaluated=req_coverage_evaluated,
            req_pass_rate_evaluated=req_pass_rate_evaluated,
            quality_evaluated=audits_evaluated,
            security_evaluated=audits_evaluated,
            architecture_evaluated=audits_evaluated,
        )

        return {
            "project_id": str(project_id),
            "health": health,
            "pass_rates": pass_rates,
            "coverage": {
                "requirement_coverage_pct": req_cov_pct,
                "total_requirements": len(requirements),
                "verified_requirements": len(req_covered_ids),
                "code_coverage_per_language": lang_coverage,
            },
            "findings_summary": {
                "total": len(findings),
                "by_severity": severity_counts,
                "top_findings": [f.model_dump(mode="json") for f in findings[:5]],
            },
        }
