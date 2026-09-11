"""
CodeSentinel Audits Module: Real SAST Tool Integration (Semgrep Scanner).

Executes Semgrep as a non-intrusive static analysis subprocess against source files,
strictly reading source files as text without executing any repository code.
Normalizes Semgrep JSON output into CodeSentinel's frozen AuditFinding schema
with proper severity mapping, standard tagging, and detected_by attribution.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import uuid

from app.core.logging import logger
from shared.schemas.audit import (
    AuditCategory,
    AuditFinding,
    AuditSeverity,
    AuditStatus,
    ComplianceStandard,
)
from shared.schemas.code_entity import CodeLocation

# Embedded Semgrep community security ruleset (Python + JS/TS) for guaranteed offline / air-gapped SAST
EMBEDDED_SEMGREP_RULES = """
rules:
  - id: python.lang.security.eval-injection
    patterns:
      - pattern-either:
          - pattern: eval(...)
          - pattern: exec(...)
    message: "Dynamic code evaluation via eval() or exec() poses severe Remote Code Execution (RCE) risk."
    languages: [python]
    severity: ERROR
    metadata:
      cwe: "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')"
      owasp: "A03:2021 - Injection"
      remediation: "Avoid dynamic code evaluation. Use ast.literal_eval for safe scalar parsing."

  - id: python.lang.security.sql-injection
    pattern-either:
      - pattern: $CURSOR.execute(f"...", ...)
      - pattern: $CURSOR.execute(f'...', ...)
      - pattern: $CURSOR.execute($X + $Y, ...)
      - pattern: $CURSOR.execute($X % $Y, ...)
      - pattern: $CURSOR.execute("...".format(...), ...)
      - pattern: $CURSOR.execute('...'.format(...), ...)
    message: "Unparameterized SQL query detected. Formatting variables into SQL strings allows SQL injection."
    languages: [python]
    severity: ERROR
    metadata:
      cwe: "CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')"
      owasp: "A03:2021 - Injection"
      remediation: "Use parameterized queries with placeholder binding (e.g., cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)))."

  - id: python.lang.security.command-injection
    patterns:
      - pattern-either:
          - pattern: os.system(...)
          - pattern: subprocess.call(..., shell=True)
          - pattern: subprocess.Popen(..., shell=True)
          - pattern: subprocess.run(..., shell=True)
    message: "Potential command injection via shell execution with unescaped input."
    languages: [python]
    severity: ERROR
    metadata:
      cwe: "CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"
      owasp: "A03:2021 - Injection"
      remediation: "Pass arguments as an argument vector list with shell=False, avoiding shell interpreters."

  - id: python.lang.security.hardcoded-secret
    patterns:
      - pattern-either:
          - pattern: $VAR = "AKIA$HEX"
          - pattern: $VAR = "ghp_$TOKEN"
          - pattern: $VAR = "-----BEGIN RSA PRIVATE KEY-----"
          - pattern: api_key = "..."
          - pattern: secret_key = "..."
    message: "Hardcoded credential or private key literal detected in source code."
    languages: [python, javascript, typescript]
    severity: ERROR
    metadata:
      cwe: "CWE-798: Use of Hard-coded Credentials"
      owasp: "A07:2021 - Identification and Authentication Failures"
      remediation: "Extract secrets to environment variables, .env files ignored by git, or secret managers."

  - id: python.lang.security.insecure-hash-algorithm
    patterns:
      - pattern-either:
          - pattern: hashlib.md5(...)
          - pattern: hashlib.sha1(...)
    message: "Cryptographically weak hashing algorithm (MD5 or SHA1) detected."
    languages: [python]
    severity: WARNING
    metadata:
      cwe: "CWE-328: Use of Weak Hash"
      owasp: "A02:2021 - Cryptographic Failures"
      remediation: "Upgrade to SHA-256 or modern password hashing functions (bcrypt, argon2id)."

  - id: python.lang.security.path-traversal
    patterns:
      - pattern-either:
          - pattern: open(os.path.join(..., $USER_INPUT), ...)
          - pattern: open(f".../{$USER_INPUT}", ...)
    message: "Potential path traversal flaw: opening file using unvalidated user path concatenation."
    languages: [python]
    severity: WARNING
    metadata:
      cwe: "CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"
      owasp: "A01:2021 - Broken Access Control"
      remediation: "Sanitize paths using os.path.abspath and assert target path resides within expected root."

  - id: javascript.lang.security.eval-injection
    patterns:
      - pattern-either:
          - pattern: eval(...)
          - pattern: Function(...)
    message: "Dynamic code execution via eval() detected in JavaScript/TypeScript code."
    languages: [javascript, typescript]
    severity: ERROR
    metadata:
      cwe: "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code"
      owasp: "A03:2021 - Injection"
      remediation: "Refactor dynamic evaluation to use standard data structures or JSON.parse."
"""


class SemgrepScanner:
    """
    Non-intrusive Static Analysis (SAST) Scanner powered by Semgrep.
    Operates strictly by reading source files as text; never executes untrusted code.
    """

    def __init__(self, semgrep_bin: Optional[str] = None):
        self.semgrep_bin = semgrep_bin or self._find_semgrep_binary()
        self._rules_path: Optional[str] = None

    def _find_semgrep_binary(self) -> Optional[str]:
        """Locate semgrep binary in active venv, PATH, or standard locations."""
        venv_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", ".venv", "Scripts", "semgrep.exe")
        venv_bin_norm = os.path.abspath(venv_bin)
        if os.path.exists(venv_bin_norm):
            return venv_bin_norm

        which_path = shutil.which("semgrep") or shutil.which("semgrep.exe")
        if which_path:
            return which_path

        return None

    def is_available(self) -> bool:
        """Returns True if Semgrep CLI binary is found on system."""
        return self.semgrep_bin is not None and os.path.exists(self.semgrep_bin)

    def _ensure_rules_file(self) -> str:
        """Writes embedded rules to a cached temporary YAML file."""
        if not self._rules_path or not os.path.exists(self._rules_path):
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
            tmp.write(EMBEDDED_SEMGREP_RULES)
            tmp.close()
            self._rules_path = tmp.name
        return self._rules_path

    def scan_source(
        self,
        project_id: uuid.UUID,
        file_path: str,
        source_code: str,
    ) -> List[AuditFinding]:
        """
        Scans an individual source file or string content using Semgrep.
        Safely writes code to a temporary scratch file (reading as text only).
        """
        if not self.is_available():
            logger.warning("Semgrep binary not detected; skipping SAST scan.")
            return []

        # Write source to temp file with original extension for proper language recognition
        ext = os.path.splitext(file_path)[1] or ".py"
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        try:
            findings = self._run_semgrep_on_path(
                target_path=tmp_path,
                project_id=project_id,
                display_file_path=file_path,
            )
            return findings
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def scan_directory(
        self,
        project_id: uuid.UUID,
        repo_root: str,
    ) -> List[AuditFinding]:
        """
        Scans an entire directory tree using Semgrep.
        """
        if not self.is_available():
            logger.warning("Semgrep binary not detected; skipping directory SAST scan.")
            return []

        return self._run_semgrep_on_path(
            target_path=repo_root,
            project_id=project_id,
            display_file_path=None,
        )

    def _run_semgrep_on_path(
        self,
        target_path: str,
        project_id: uuid.UUID,
        display_file_path: Optional[str] = None,
    ) -> List[AuditFinding]:
        """Executes semgrep subprocess and parses findings."""
        rules_file = self._ensure_rules_file()

        cmd = [
            self.semgrep_bin,  # type: ignore
            "scan",
            "--config", rules_file,
            "--json",
            "--metrics=off",
            "--disable-version-check",
            target_path,
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
            )
            output = res.stdout or "{}"
            data = json.loads(output)
            raw_results = data.get("results", [])
            return self._parse_semgrep_results(
                results=raw_results,
                project_id=project_id,
                target_path=target_path,
                display_file_path=display_file_path,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Semgrep scan timed out after 45s on {target_path}")
            return []
        except Exception as e:
            logger.warning(f"Error running Semgrep scan: {e}")
            return []

    def _parse_semgrep_results(
        self,
        results: List[Dict[str, Any]],
        project_id: uuid.UUID,
        target_path: str,
        display_file_path: Optional[str] = None,
    ) -> List[AuditFinding]:
        """Maps Semgrep JSON results to AuditFinding domain models."""
        findings: List[AuditFinding] = []

        for item in results:
            check_id = item.get("check_id", "SEMGREP-GENERIC-VULNERABILITY")
            extra = item.get("extra", {})
            raw_severity = extra.get("severity", "WARNING").upper()
            message = extra.get("message", "Semgrep security finding detected.")
            metadata = extra.get("metadata", {})

            # Map Semgrep Severity to AuditSeverity
            severity = self._map_severity(raw_severity, check_id)

            # Location calculation
            start_pos = item.get("start", {})
            end_pos = item.get("end", {})
            start_line = start_pos.get("line", 1)
            end_line = end_pos.get("line", start_line)
            start_col = start_pos.get("col", 1)
            end_col = end_pos.get("col", 1)

            # Normalise file path
            item_path = item.get("path", target_path)
            if display_file_path:
                norm_file_path = display_file_path
            elif os.path.isabs(item_path):
                norm_file_path = os.path.relpath(item_path, target_path) if os.path.isdir(target_path) else os.path.basename(item_path)
            else:
                norm_file_path = item_path
            norm_file_path = norm_file_path.replace("\\", "/")

            # Compliance standard references
            cwe_info = metadata.get("cwe", "")
            cwe_str = cwe_info[0] if isinstance(cwe_info, list) and cwe_info else str(cwe_info)
            cwe_id = cwe_str.split(":")[0].strip() if ":" in cwe_str else (cwe_str or "CWE-General")

            remediation = metadata.get("remediation") or extra.get("fix") or "Review and sanitize input parameters."

            finding = AuditFinding(
                id=uuid.uuid4(),
                project_id=project_id,
                rule_id=f"SEMGREP-{check_id.upper().replace('.', '-')}",
                title=f"Security Flaw: {check_id.split('.')[-1].replace('-', ' ').title()}",
                description=f"{message} (Rule: {check_id})",
                category=AuditCategory.SECURITY_VULNERABILITY,
                severity=severity,
                standard=ComplianceStandard.CWE if cwe_id else ComplianceStandard.OWASP_TOP_10,
                standard_reference_id=cwe_id,
                location=CodeLocation(
                    file_path=norm_file_path,
                    start_line=start_line,
                    end_line=end_line,
                    start_column=start_col,
                    end_column=end_col,
                ),
                remediation_suggestion=remediation,
                status=AuditStatus.OPEN,
                cvss_score=8.5 if severity == AuditSeverity.CRITICAL else (7.5 if severity == AuditSeverity.HIGH else 5.5),
                detected_by=["semgrep"],
            )
            findings.append(finding)

        return findings

    @staticmethod
    def _map_severity(raw_severity: str, check_id: str) -> AuditSeverity:
        """Normalizes Semgrep severity into CodeSentinel AuditSeverity."""
        lowered_id = check_id.lower()
        if raw_severity == "ERROR":
            if any(k in lowered_id for k in ["eval", "rce", "command-injection", "secret", "sql-injection"]):
                return AuditSeverity.CRITICAL
            return AuditSeverity.HIGH
        elif raw_severity == "WARNING":
            return AuditSeverity.MEDIUM
        elif raw_severity in ("INFO", "EXPERIMENT"):
            return AuditSeverity.LOW
        return AuditSeverity.MEDIUM


# Singleton instance for audit workflows
semgrep_scanner = SemgrepScanner()
