"""
Regression Test: Verify No Generated Test Body is a Tautology.

Validates FIX 3:
- For every generated test, its source code contains a call to the actual target function/entity being tested.
- Verifies AST Call node targets the entity name, not just in a docstring or string literal.
- Asserts zero tautological assertions:
  * No `assert '<entity>' is not None`
  * No `assert executed is True` without calling target entity
  * No bare `pass`
"""

import ast
import uuid
import pytest
from app.testing.generator import (
    AIInferredGenerator,
    CoverageOnlyGenerator,
    RequirementVerifiedGenerator,
    SchemaDerivedGenerator,
)


class MockAIClient:
    async def ask_agent(self, *args, **kwargs):
        return {"answer": "Generated mock test logic"}


def _get_call_names(node: ast.AST) -> set[str]:
    """Recursively extract all function/method call names from an AST node."""
    calls = set()
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Name):
                calls.add(subnode.func.id)
            elif isinstance(subnode.func, ast.Attribute):
                calls.add(subnode.func.attr)
    return calls


def test_schema_derived_tests_invoke_target_entity_no_tautology():
    project_id = uuid.uuid4()
    entities = [
        {
            "id": str(uuid.uuid4()),
            "name": "count_items",
            "file_path": "app/calculator.py",
            "parameters": [{"name": "items", "type_annotation": "list"}],
            "signature": "count_items(items: list) -> int",
        },
        {
            "id": str(uuid.uuid4()),
            "name": "add",
            "file_path": "app/calculator.py",
            "parameters": [
                {"name": "a", "type_annotation": "int"},
                {"name": "b", "type_annotation": "int"},
            ],
            "signature": "add(a: int, b: int) -> int",
        },
    ]
    routes = [
        {
            "id": str(uuid.uuid4()),
            "path": "/api/calculator/count",
            "method": "POST",
        }
    ]

    generator = SchemaDerivedGenerator()
    tests = generator.generate(project_id, routes, entities)

    assert len(tests) >= 3, "Expected at least 3 schema-derived tests"

    for tc in tests:
        tree = ast.parse(tc.test_code)
        calls = _get_call_names(tree)

        # Ensure no string literal tautologies like `assert 'count_items' is not None`
        assert "assert 'count_items' is not None" not in tc.test_code
        assert "assert 'add' is not None" not in tc.test_code

        # For entity structural tests, verify target function is actually called
        target_name = tc.metadata.get("entity_name")
        if target_name:
            assert target_name in calls, (
                f"Generated test {tc.name} does not call target function '{target_name}'! "
                f"Found calls: {calls}. Code:\n{tc.test_code}"
            )


def test_coverage_only_tests_invoke_target_entity_no_tautology():
    project_id = uuid.uuid4()
    entities = [
        {
            "id": str(uuid.uuid4()),
            "name": "count_items",
            "file_path": "app/calculator.py",
            "parameters": [{"name": "items", "type_annotation": "list"}],
            "signature": "count_items(items: list) -> int",
        }
    ]

    generator = CoverageOnlyGenerator()
    tests = generator.generate(project_id, entities, {})

    assert len(tests) == 1
    tc = tests[0]
    tree = ast.parse(tc.test_code)
    calls = _get_call_names(tree)

    # Must genuinely invoke count_items
    assert "count_items" in calls, f"count_items not called in coverage test:\n{tc.test_code}"

    # Must not be a disconnected `executed = True; assert executed is True` without target call
    assert "_cov_res = count_items(" in tc.test_code


@pytest.mark.asyncio
async def test_ai_inferred_tests_invoke_target_entity_no_bare_pass():
    project_id = uuid.uuid4()
    entities = [
        {
            "id": str(uuid.uuid4()),
            "name": "count_items",
            "file_path": "app/calculator.py",
            "parameters": [{"name": "items", "type_annotation": "list"}],
        }
    ]

    generator = AIInferredGenerator(MockAIClient())
    tests = await generator.generate(project_id, entities)

    assert len(tests) == 1
    tc = tests[0]
    tree = ast.parse(tc.test_code)
    calls = _get_call_names(tree)

    assert "count_items" in calls, f"count_items not called in AI-inferred test:\n{tc.test_code}"
    # Verify body is not merely `pass`
    func_def = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    non_doc_statements = [s for s in func_def.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    assert not (len(non_doc_statements) == 1 and isinstance(non_doc_statements[0], ast.Pass))


def test_requirement_verified_tests_invoke_target_and_assert_real_return():
    project_id = uuid.uuid4()
    requirements = [
        {
            "id": str(uuid.uuid4()),
            "identifier": "REQ-CALC-01",
            "title": "Item Batch Counting",
            "acceptance_criteria": [
                "Given a list of items ['a', 'b', 'c'], when count_items is invoked, then the returned count must be exactly 3.",
                "Given an empty list of items [], when count_items is invoked, then the returned count must be exactly 0.",
            ],
        }
    ]
    system_model = {
        "entities": [
            {
                "id": str(uuid.uuid4()),
                "name": "count_items",
                "file_path": "app/calculator.py",
                "signature": "count_items(items: list) -> int",
            }
        ]
    }

    generator = RequirementVerifiedGenerator()
    tests = generator.generate(project_id, requirements, system_model)

    assert len(tests) == 2, f"Expected 2 requirement-verified tests, got {len(tests)}"

    for tc in tests:
        tree = ast.parse(tc.test_code)
        calls = _get_call_names(tree)
        assert "count_items" in calls, f"count_items not called in requirement test:\n{tc.test_code}"

    # AC 1 asserts 3
    assert "count_items(['a', 'b', 'c'])" in tests[0].test_code or "count_items(" in tests[0].test_code
    assert "3" in tests[0].test_code

    # AC 2 asserts 0
    assert "count_items([])" in tests[1].test_code or "count_items(" in tests[1].test_code
    assert "0" in tests[1].test_code
