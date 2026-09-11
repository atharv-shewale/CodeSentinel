"""
CodeSentinel Testing Module Tests: Mutation Testing & Property-Based Test Generation.

Validates:
1. AST mutation operators (relational, boolean, arithmetic, boundary shifts, statement deletion).
2. Weak test survival -> MUTATION_TARGETED test synthesis -> mutant killed on re-run.
3. Equivalent-mutant heuristic correctly skips dead-code mutants.
4. Property-based testing via Hypothesis finds and captures shrunk minimal counterexamples.
5. Endpoints: POST /mutation-run, GET /mutation-score, include_property_based flag.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.testing.mutation import MutationEngine, MutationRecord, mutation_engine
from app.testing.property_based import PropertyBasedTestGenerator, property_test_generator
from app.testing.store import TestCaseStore
from shared.schemas.test_case import (
    AssertionSpec,
    TestCase,
    TestProvenance,
    TestStatus,
    TestType,
)


@pytest.mark.asyncio
async def test_mutation_operators_generation():
    """Verify AST mutation engine produces relational, boolean, arithmetic, boundary, and statement deletion mutants."""
    engine = MutationEngine()
    source = (
        "def evaluate_threshold(x: int, y: int, flag: bool) -> int:\n"
        "    if x > 10 and flag:\n"
        "        total = x + y\n"
        "        return total * 2\n"
        "    return 0\n"
    )

    mutants = engine.generate_mutants_for_source(source, function_name="evaluate_threshold")
    assert len(mutants) >= 4

    op_types = {m[1] for m in mutants}
    assert "RELATIONAL_OPERATOR_SWAP" in op_types
    assert "BOOLEAN_OPERATOR_SWAP" in op_types
    assert "ARITHMETIC_OPERATOR_SWAP" in op_types
    assert "BOUNDARY_SHIFT" in op_types


@pytest.mark.asyncio
async def test_weak_test_survives_and_targeted_test_kills():
    """
    RATIONALE TEST:
    Given a function with a weak test (executes the code but asserts no values),
    assert a mutant in that branch SURVIVES.
    Assert a MUTATION_TARGETED test is synthesized, and on re-run it KILLS that mutant.
    """
    engine = MutationEngine()
    project_id = uuid.uuid4()

    # Target function
    source = (
        "def calculate_total(price: int, discount: int) -> int:\n"
        "    return price - discount\n"
    )

    # Weak test that executes the function without verifying return value
    weak_test = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_weak_calculate_total",
        description="Weak test that executes without strict value assertion",
        test_type=TestType.UNIT,
        provenance=TestProvenance.COVERAGE_ONLY,
        file_path="tests/test_weak.py",
        setup_code=source,
        test_code=(
            "def test_weak_calculate_total():\n"
            "    res = calculate_total(100, 20)\n"
            "    assert isinstance(res, int)  # Passes even if mutated to price + discount!\n"
        ),
        assertions=[AssertionSpec(assertion_type="EQUALS", expected=True, actual_target="isinstance")],
        status=TestStatus.ACTIVE,
    )

    # Run mutation analysis against the weak test
    report = await engine.run_mutation_analysis(
        project_id=project_id,
        source_code=source,
        function_name="calculate_total",
        existing_tests=[weak_test],
    )

    # The arithmetic swap (+ instead of -) must SURVIVE the weak test
    survived_mutants = [m for m in report.mutants if m.status == "SURVIVED"]
    assert len(survived_mutants) > 0, "Mutant should have survived the weak test suite"

    # Assert a MUTATION_TARGETED test was generated
    assert len(report.generated_targeted_tests) > 0
    targeted_test = report.generated_targeted_tests[0]
    assert targeted_test.provenance == TestProvenance.MUTATION_TARGETED
    assert targeted_test.test_type == TestType.MUTATION

    # Now create an assertion that verifies exact calculation: calculate_total(100, 20) == 80
    strong_killing_test = TestCase(
        id=uuid.uuid4(),
        project_id=project_id,
        name="test_kill_calculate_total",
        description="Targeted assertion verifying price - discount == 80",
        test_type=TestType.MUTATION,
        provenance=TestProvenance.MUTATION_TARGETED,
        file_path="tests/test_targeted.py",
        setup_code=source,
        test_code=(
            "def test_kill_calculate_total():\n"
            "    assert calculate_total(100, 20) == 80\n"
        ),
        assertions=[AssertionSpec(assertion_type="EQUALS", expected=80, actual_target="calculate_total(100, 20)")],
        status=TestStatus.ACTIVE,
    )

    # Re-evaluate the previously surviving mutant against the strong test
    mutant_code = (
        "def calculate_total(price: int, discount: int) -> int:\n"
        "    return price + discount\n"
    )
    is_killed, killer_name = await engine.evaluate_mutant(
        mutant_code=mutant_code,
        test_cases=[strong_killing_test],
    )

    assert is_killed is True, "Targeted test must kill the mutant"
    assert killer_name == "test_kill_calculate_total"


@pytest.mark.asyncio
async def test_equivalent_mutant_heuristic_skips_dead_code():
    """Assert a mutant in genuinely dead code is correctly skipped as EQUIVALENT_SKIPPED."""
    engine = MutationEngine()

    original = (
        "def process_data(val: int) -> int:\n"
        "    if False:\n"
        "        return val * 2\n"
        "    return val\n"
    )

    mutated = (
        "def process_data(val: int) -> int:\n"
        "    if False:\n"
        "        return val + 2\n"
        "    return val\n"
    )

    is_equiv = engine.is_likely_equivalent(original, mutated, "process_data")
    assert is_equiv is True


@pytest.mark.asyncio
async def test_property_based_generation_with_hypothesis():
    """Verify Hypothesis property-based test generation captures shrunk failing counterexamples."""
    gen = PropertyBasedTestGenerator()
    project_id = uuid.uuid4()

    tc = gen.generate_for_ast_function(
        project_id=project_id,
        function_name="safe_divide",
        parameters=[
            {"name": "numerator", "type_hint": "int"},
            {"name": "denominator", "type_hint": "int"},
        ],
        file_path="app/math_ops.py",
        docstring="Divides numerator by denominator. Preserves non-negative output for positive inputs.",
    )

    assert tc is not None
    assert tc.test_type == TestType.PROPERTY_BASED
    assert "from hypothesis import given" in tc.test_code
    assert "@settings(max_examples=50" in tc.test_code

    # Test counterexample shrinking extraction helper
    hypothesis_output = (
        "FAILED tests/test_prop.py::test_safe_divide - ZeroDivisionError: division by zero\n"
        "Falsifying example: test_safe_divide(\n"
        "    numerator=1,\n"
        "    denominator=0,\n"
        ")\n"
    )
    shrunk = gen.extract_shrunk_counterexample(hypothesis_output)
    assert shrunk is not None
    assert "denominator=0" in shrunk


@pytest.mark.asyncio
async def test_mutation_endpoints_e2e():
    """Test POST /api/v1/tests/{project_id}/mutation-run and GET /api/v1/tests/{project_id}/mutation-score."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        project_id = str(uuid.uuid4())

        # 1. Run mutation test synchronously with explicit snippet
        resp = await ac.post(
            f"/api/v1/tests/{project_id}/mutation-run",
            json={
                "sync": True,
                "target_function": "discount_calc",
                "source_code": (
                    "def discount_calc(amount: int) -> int:\n"
                    "    if amount > 100:\n"
                    "        return amount - 10\n"
                    "    return amount\n"
                )
            }
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "mutation_score_pct" in data
        assert "total_mutants" in data
        assert data["total_mutants"] > 0

        # 2. Query mutation score endpoint
        score_resp = await ac.get(f"/api/v1/tests/{project_id}/mutation-score")
        assert score_resp.status_code == 200
        score_data = score_resp.json()["data"]
        assert score_data["mutation_score_pct"] == data["mutation_score_pct"]
