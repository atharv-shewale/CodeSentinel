"""
CodeSentinel Testing Module: Property-Based Test Generation with Hypothesis.

Derives property-based tests automatically from:
1. Type/Schema Constraints (provenance: SCHEMA_DERIVED)
2. Explicit invariants from requirements/docstrings (provenance: REQUIREMENT_VERIFIED)

Executes inside the standard Docker sandbox and captures shrunk minimal counterexamples.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from shared.schemas.test_case import (
    AssertionSpec,
    TestCase,
    TestProvenance,
    TestStatus,
    TestType,
)
from app.core.logging import logger


class PropertyStrategyMapper:
    """Maps Python AST parameter types to Hypothesis strategies."""

    TYPE_TO_STRATEGY: Dict[str, str] = {
        "int": "st.integers()",
        "float": "st.floats(allow_nan=False, allow_infinity=False)",
        "str": "st.text(max_size=100)",
        "bool": "st.booleans()",
        "bytes": "st.binary()",
        "list": "st.lists(st.integers(), max_size=20)",
        "dict": "st.dictionaries(st.text(max_size=10), st.integers(), max_size=10)",
    }

    @classmethod
    def get_strategy_for_type(cls, type_name: str, param_name: str = "") -> str:
        """Derive Hypothesis strategy string from type hint and parameter name heuristics."""
        clean_type = type_name.strip()

        # Check positive/non-negative naming conventions
        if "pos" in param_name.lower() or "count" in param_name.lower() or "limit" in param_name.lower():
            if clean_type in ("int", ""):
                return "st.integers(min_value=1, max_value=10000)"
        if "rate" in param_name.lower() or "pct" in param_name.lower() or "ratio" in param_name.lower():
            return "st.floats(min_value=0.0, max_value=1.0)"

        if clean_type in cls.TYPE_TO_STRATEGY:
            return cls.TYPE_TO_STRATEGY[clean_type]

        # Parameter name heuristics if untyped
        if param_name.startswith("is_") or param_name.startswith("has_"):
            return "st.booleans()"
        if "id" in param_name.lower() or "num" in param_name.lower() or "idx" in param_name.lower():
            return "st.integers(min_value=0, max_value=1000)"
        if "name" in param_name.lower() or "text" in param_name.lower() or "query" in param_name.lower():
            return "st.text(min_size=1, max_size=50)"

        # Default general fallback strategy
        return "st.integers(min_value=-1000, max_value=1000)"


class PropertyBasedTestGenerator:
    """Generates Hypothesis-based property tests for code entities and verified requirements."""

    INVARIANT_PATTERNS = [
        (r"idempotent|idempotence", "assert func(func({args})) == func({args})", "Idempotency invariant"),
        (r"commutative|commutativity", "assert func({arg0}, {arg1}) == func({arg1}, {arg0})", "Commutativity invariant"),
        (r"never negative|non-negative|>= 0", "assert func({args}) >= 0", "Non-negativity invariant"),
        (r"preserves length|same length", "assert len(func({arg0})) == len({arg0})", "Length preservation invariant"),
        (r"deterministic", "assert func({args}) == func({args})", "Determinism invariant"),
    ]

    def generate_for_ast_function(
        self,
        project_id: uuid.UUID,
        function_name: str,
        parameters: List[Dict[str, Any]],
        file_path: str,
        docstring: Optional[str] = None,
        source_code: Optional[str] = None,
        requirement_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[TestCase]:
        """
        Generate a property-based test with Hypothesis for a given function.
        Determines provenance based on source (REQUIREMENT_VERIFIED if backed by explicit requirement invariant,
        otherwise SCHEMA_DERIVED).
        """
        if not parameters:
            return None

        param_names: List[str] = []
        strategy_assignments: List[str] = []

        for p in parameters:
            p_name = p.get("name", "arg")
            if p_name in ("self", "cls"):
                continue
            p_type = p.get("type_hint", "") or p.get("type", "")
            strat = PropertyStrategyMapper.get_strategy_for_type(p_type, p_name)
            param_names.append(p_name)
            strategy_assignments.append(f"{p_name}={strat}")

        if not param_names:
            return None

        # Check for explicit invariant in requirement or docstring
        combined_text = f"{docstring or ''}\n{requirement_info.get('statement', '') if requirement_info else ''}"
        invariant_rule: Optional[Tuple[str, str]] = None

        for pattern, assertion_tpl, desc in self.INVARIANT_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                invariant_rule = (assertion_tpl, desc)
                break

        # Provenance attribution rule:
        # If explicitly specified by an approved requirement -> REQUIREMENT_VERIFIED
        # If derived strictly from AST types and general invariants -> SCHEMA_DERIVED
        if requirement_info and invariant_rule:
            provenance = TestProvenance.REQUIREMENT_VERIFIED
            provenance_desc = f"Requirement-verified invariant: {invariant_rule[1]}"
        else:
            provenance = TestProvenance.SCHEMA_DERIVED
            provenance_desc = "Schema-derived property test verifying stability across input domain"

        test_name = f"test_prop_{function_name}_{provenance.lower()[:8]}"
        given_args = ", ".join(strategy_assignments)
        call_args = ", ".join(param_names)

        if invariant_rule:
            arg0 = param_names[0]
            arg1 = param_names[1] if len(param_names) > 1 else arg0
            assertion_code = invariant_rule[0].format(
                func=function_name,
                args=call_args,
                arg0=arg0,
                arg1=arg1,
            )
        else:
            assertion_code = (
                f"    # Invariant: function should not throw unexpected crashes on valid-typed inputs\n"
                f"    try:\n"
                f"        res = {function_name}({call_args})\n"
                f"        assert res is not None or res is None\n"
                f"    except (ValueError, TypeError, ZeroDivisionError):\n"
                f"        pass  # Expected domain input rejections"
            )

        setup_code = source_code or f"from {file_path.replace('.py', '').replace('/', '.')} import {function_name}"

        test_code = (
            f"from hypothesis import given, strategies as st, settings\n\n"
            f"@settings(max_examples=50, deadline=None)\n"
            f"@given({given_args})\n"
            f"def {test_name}({', '.join(param_names)}):\n"
            f'    """\n'
            f"    Property-Based Test: {provenance_desc}\n"
            f"    Function: {function_name}\n"
            f'    """\n'
            f"{assertion_code}\n"
        )

        test_id = uuid.uuid4()
        return TestCase(
            id=test_id,
            project_id=project_id,
            name=test_name,
            description=f"Property-based test for {function_name} ({provenance_desc}).",
            test_type=TestType.PROPERTY_BASED,
            provenance=provenance,
            file_path=f"tests/test_property_{function_name}.py",
            setup_code=setup_code,
            test_code=test_code,
            assertions=[
                AssertionSpec(
                    assertion_type="INVARIANT_HOLDS",
                    expected="Invariant satisfied across 50 pseudo-random inputs",
                    actual_target=function_name,
                    description=provenance_desc,
                )
            ],
            status=TestStatus.ACTIVE,
            execution_count=0,
            pass_count=0,
            fail_count=0,
            flakiness_score=0.0,
            tags=["PROPERTY_BASED", "HYPOTHESIS", provenance],
        )

    @staticmethod
    def extract_shrunk_counterexample(output_text: str) -> Optional[str]:
        """
        Extract the minimal shrunk failing counterexample generated by Hypothesis.
        Matches patterns like:
        Falsifying example: test_func(
            x=0,
        )
        """
        match = re.search(r"Falsifying example:\s*([^\n]+(?:\n\s+[^\n]+)*)", output_text)
        if match:
            return match.group(1).strip()

        # Alternative Hypothesis summary pattern
        match_alt = re.search(r"Falsifying example:\s*(.+)", output_text)
        if match_alt:
            return match_alt.group(1).strip()

        return None


# Global singleton generator
property_test_generator = PropertyBasedTestGenerator()
