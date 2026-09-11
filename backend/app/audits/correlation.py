"""
CodeSentinel Audits Module: Multi-Scanner Finding Correlation & Deduplication Engine.

Aggregates findings from Semgrep, regex pattern detectors, and dependency checkers.
Merges findings that share the same file path, overlapping line ranges, and similar
category/CWE into a single unified AuditFinding with a combined `detected_by` list.
"""

from __future__ import annotations

import copy
from typing import List
import uuid

from shared.schemas.audit import (
    AuditCategory,
    AuditFinding,
    AuditSeverity,
)
from shared.schemas.code_entity import CodeLocation

SEVERITY_ORDER = {
    AuditSeverity.CRITICAL: 5,
    AuditSeverity.HIGH: 4,
    AuditSeverity.MEDIUM: 3,
    AuditSeverity.LOW: 2,
    AuditSeverity.INFO: 1,
}


class FindingCorrelator:
    """
    Deduplicates and correlates findings emitted across multiple static analyzers and tools.
    """

    @staticmethod
    def _is_line_overlap(loc1: CodeLocation, loc2: CodeLocation) -> bool:
        """Determines whether two coordinate locations share overlapping line ranges."""
        return max(loc1.start_line, loc2.start_line) <= min(loc1.end_line, loc2.end_line)

    @staticmethod
    def _is_similar_category(f1: AuditFinding, f2: AuditFinding) -> bool:
        """Determines whether two findings share similar category, CWE, or defect domain."""
        # Distinct vulnerable dependency packages should never be merged
        is_dep1 = "VULN-DEP" in f1.rule_id
        is_dep2 = "VULN-DEP" in f2.rule_id
        if is_dep1 or is_dep2:
            return is_dep1 and is_dep2 and f1.rule_id == f2.rule_id

        # If both are secrets
        is_secret1 = "SECRET" in f1.rule_id or "secret" in f1.title.lower() or "credential" in f1.title.lower()
        is_secret2 = "SECRET" in f2.rule_id or "secret" in f2.title.lower() or "credential" in f2.title.lower()
        if is_secret1 or is_secret2:
            return is_secret1 and is_secret2

        # If both are code injection / eval
        is_inj1 = "INJECTION" in f1.rule_id or "eval" in f1.rule_id.lower()
        is_inj2 = "INJECTION" in f2.rule_id or "eval" in f2.rule_id.lower()
        if is_inj1 or is_inj2:
            return is_inj1 and is_inj2

        # Check CWE alignment
        if f1.standard_reference_id and f2.standard_reference_id:
            cwe1 = f1.standard_reference_id.split("-")[-1].split(":")[0]
            cwe2 = f2.standard_reference_id.split("-")[-1].split(":")[0]
            if cwe1 == cwe2:
                return True

        if f1.category == f2.category:
            return True

        return False

    @classmethod
    def correlate_and_deduplicate(
        cls,
        findings: List[AuditFinding],
    ) -> List[AuditFinding]:
        """
        Takes an arbitrary list of findings from multiple tools, merges duplicates
        on (file_path, line_overlap, category/CWE), and populates a combined `detected_by` list.
        """
        if not findings:
            return []

        # Partition findings by file path
        by_file: dict[str, List[AuditFinding]] = {}
        for f in findings:
            file_key = (f.location.file_path or "").replace("\\", "/").strip().lower()
            by_file.setdefault(file_key, []).append(f)

        deduplicated: List[AuditFinding] = []

        for file_key, file_findings in by_file.items():
            clusters: List[List[AuditFinding]] = []

            for f in file_findings:
                matched_cluster = None
                for cluster in clusters:
                    # Check if finding overlaps with any finding in the cluster
                    for c_finding in cluster:
                        if cls._is_line_overlap(f.location, c_finding.location) and cls._is_similar_category(f, c_finding):
                            matched_cluster = cluster
                            break
                    if matched_cluster:
                        break

                if matched_cluster:
                    matched_cluster.append(f)
                else:
                    clusters.append([f])

            # Merge each cluster into a single canonical finding
            for cluster in clusters:
                if len(cluster) == 1:
                    deduplicated.append(cluster[0])
                else:
                    merged = cls._merge_finding_cluster(cluster)
                    deduplicated.append(merged)

        return deduplicated

    @classmethod
    def _merge_finding_cluster(cls, cluster: List[AuditFinding]) -> AuditFinding:
        """Combines multiple matching findings into a single correlated finding."""
        # Sort cluster by highest severity first, then prefer native CodeSentinel rule IDs over third-party prefixes
        sorted_cluster = sorted(
            cluster,
            key=lambda item: (
                SEVERITY_ORDER.get(item.severity, 0),
                0 if item.rule_id.startswith("SEMGREP-") else 1,
            ),
            reverse=True,
        )
        canonical = copy.deepcopy(sorted_cluster[0])

        # Combine detected_by list
        all_detectors = set()
        for f in cluster:
            if f.detected_by:
                all_detectors.update(f.detected_by)
            else:
                all_detectors.add("codesentinel-static-analyzer")
        canonical.detected_by = sorted(list(all_detectors))

        # Highest severity is already canonical.severity
        # Bounding line range
        min_start = min(f.location.start_line for f in cluster)
        max_end = max(f.location.end_line for f in cluster)
        canonical.location.start_line = min_start
        canonical.location.end_line = max_end

        # Highest CVSS score
        max_cvss = max((f.cvss_score for f in cluster if f.cvss_score is not None), default=None)
        canonical.cvss_score = max_cvss

        # Augment description with confirmation from other tools
        tool_list_str = ", ".join(canonical.detected_by)
        canonical.description = (
            f"{canonical.description}\n"
            f"[Correlated across {len(canonical.detected_by)} tools: {tool_list_str}]"
        )

        return canonical


finding_correlator = FindingCorrelator()
