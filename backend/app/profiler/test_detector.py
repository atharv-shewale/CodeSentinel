"""
CodeSentinel Profiler: Existing Test Suite Detector.

Discovers existing test suites across Python (pytest, unittest) and JS/TS (jest, mocha, vitest)
and records file paths and detected test frameworks without executing code.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Set
from app.ingestion.file_scanner import ScanResult


class TestDetector:
    """Detects test files and test execution frameworks."""

    @classmethod
    def detect_all(cls, root_dir: str, scan_result: ScanResult) -> Dict[str, Any]:
        """
        Identify test files and infer test frameworks.
        """
        test_files: List[str] = []
        frameworks: Set[str] = set()

        for file in scan_result.files:
            rel_lower = file.relative_path.lower()
            filename = os.path.basename(rel_lower)

            # Python Tests
            if file.language == "python":
                is_test = (
                    filename.startswith("test_")
                    or filename.endswith("_test.py")
                    or "/tests/" in rel_lower
                    or rel_lower.startswith("tests/")
                    or "/test/" in rel_lower
                )
                if is_test:
                    test_files.append(file.relative_path)
                    # Check framework
                    try:
                        with open(file.absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read(2048)
                            if "pytest" in content:
                                frameworks.add("pytest")
                            if "unittest" in content:
                                frameworks.add("unittest")
                    except Exception:
                        pass

            # JS/TS Tests
            elif file.language in ("javascript", "typescript"):
                is_test = (
                    filename.endswith(".test.js")
                    or filename.endswith(".test.ts")
                    or filename.endswith(".test.jsx")
                    or filename.endswith(".test.tsx")
                    or filename.endswith(".spec.js")
                    or filename.endswith(".spec.ts")
                    or filename.endswith(".spec.jsx")
                    or filename.endswith(".spec.tsx")
                    or "__tests__" in rel_lower
                )
                if is_test:
                    test_files.append(file.relative_path)
                    try:
                        with open(file.absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read(2048)
                            if "vitest" in content:
                                frameworks.add("vitest")
                            elif "jest" in content or "describe(" in content or "it(" in content:
                                frameworks.add("jest")
                            elif "mocha" in content:
                                frameworks.add("mocha")
                    except Exception:
                        pass

        # Check package.json / pyproject.toml for explicit test runners if frameworks empty
        if test_files and not frameworks:
            frameworks.add("pytest" if any(f.endswith(".py") for f in test_files) else "jest")

        return {
            "has_tests": len(test_files) > 0,
            "total_test_files": len(test_files),
            "test_files": test_files,
            "test_frameworks": sorted(list(frameworks)),
        }
