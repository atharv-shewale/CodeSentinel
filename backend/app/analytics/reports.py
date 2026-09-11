"""
CodeSentinel Reports Submodule: Multi-Format Report Generator.

Generates unified project health reports combining:
- Executive Overview & Health Score breakdown
- Audit Findings Summary
- Tiered Test Pass Rates
- Traceability Matrix
Exportable as Markdown and structured JSON.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
from shared.schemas.common import utc_now
from app.analytics.engine import AnalyticsEngine
from app.audits.store import AuditFindingStore


class ReportGenerator:
    """Generates structured intelligence reports in Markdown and JSON."""

    def __init__(
        self,
        analytics_engine: Optional[AnalyticsEngine] = None,
        audit_store: Optional[AuditFindingStore] = None,
    ):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.audit_store = audit_store or AuditFindingStore()

    async def generate_markdown_report(self, project_id: uuid.UUID) -> str:
        """Generate a complete Markdown Project Health Report."""
        data = await self.analytics.get_project_analytics(project_id)
        health = data["health"]
        pass_rates = data["pass_rates"]
        cov = data["coverage"]
        findings = data["findings_summary"]

        system_model = await self.analytics.client.get_system_model(project_id) or {}
        tests = await self.analytics.client.get_tests(project_id)
        execs = await self.analytics.client.get_executions(project_id)
        traceability = AnalyticsEngine.build_traceability_matrix(
            requirements=system_model.get("requirements", []),
            entities=system_model.get("entities", []),
            test_cases=tests,
            executions=execs,
        )

        md = f"""# CodeSentinel Project Health & Intelligence Report
**Project ID:** `{project_id}`  
**Generated At:** {utc_now().isoformat()}  
**Overall Grade:** **{health['grade']}** ({health['health_score']}/100)

---

## 1. Executive Summary & Health Score Breakdown
The overall project health score is computed deterministically using the transparent formula:
`{health['formula']}`

| Component | Weight | Score | Details |
|---|---|---|---|
| **Requirement Coverage** | 35% | {health['components']['requirement_coverage']['score']}% | {cov['verified_requirements']}/{cov['total_requirements']} verified |
| **Requirement Pass Rate** | 25% | {health['components']['requirement_pass_rate']['score']}% | Pass rate of Tier 1 tests |
| **Code Quality** | 15% | {health['components']['code_quality']['score']}% | Penalty: -{health['components']['code_quality']['penalty']} pts |
| **Security Posture** | 15% | {health['components']['security']['score']}% | Penalty: -{health['components']['security']['penalty']} pts |
| **Architecture Health**| 10% | {health['components']['architecture']['score']}% | Penalty: -{health['components']['architecture']['penalty']} pts |

---

## 2. Test Execution & Tiered Pass Rates
Pass rates broken down by mandatory provenance tiers:

| Provenance Tier | Total Runs | Passed | Failed | Errors | Pass Rate |
|---|---|---|---|---|---|
"""
        for tier, stats in pass_rates["by_provenance"].items():
            md += f"| `{tier}` | {stats['total_runs']} | {stats['passed']} | {stats['failed']} | {stats['errors']} | **{stats['pass_rate_pct']}%** |\n"

        md += f"\n**Overall Pass Rate:** {pass_rates['overall_pass_rate_pct']}%\n\n---\n\n## 3. Code Coverage by Ecosystem\n"
        for lang, pct in cov["code_coverage_per_language"].items():
            md += f"- **{lang}:** {pct}%\n"

        md += f"""
---

## 4. Audit Findings Summary
Total Open Findings: **{findings['total']}**  
- Critical: `{findings['by_severity']['CRITICAL']}`
- High: `{findings['by_severity']['HIGH']}`
- Medium: `{findings['by_severity']['MEDIUM']}`
- Low: `{findings['by_severity']['LOW']}`

---

## 5. Traceability Matrix (Requirements -> Code -> Tests -> Executions)

| Req ID | Title | Entity | Test Name | Provenance | Execution Status |
|---|---|---|---|---|---|
"""
        sorted_traceability = sorted(
            traceability,
            key=lambda x: (0 if x.get("requirement_identifier") not in ("N/A", "REQ-GAP") else 1)
        )
        for item in sorted_traceability[:50]:
            md += f"| `{item['requirement_identifier']}` | {item['requirement_title'][:30]} | `{item['entity_name'][:25]}` | `{item['test_name']}` | `{item['provenance']}` | **{item['execution_status']}** |\n"

        if len(traceability) > 50:
            md += f"\n*(Showing top 50 of {len(traceability)} traceability records)*\n"

        return md

    async def generate_json_report(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Generate a complete structured JSON Project Health Report."""
        data = await self.analytics.get_project_analytics(project_id)
        markdown = await self.generate_markdown_report(project_id)
        return {
            "project_id": str(project_id),
            "generated_at": utc_now().isoformat(),
            "grade": data["health"]["grade"],
            "health_score": data["health"]["health_score"],
            "analytics": data,
            "markdown_content": markdown,
        }
