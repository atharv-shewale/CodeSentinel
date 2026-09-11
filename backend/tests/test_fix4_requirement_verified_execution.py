import uuid
import pytest
import sys
from pathlib import Path

from app.testing.generator import RequirementVerifiedGenerator
from app.requirements.extractor import RequirementExtractor


def test_fix4_requirement_verified_catches_off_by_one():
    # 1. Parse real requirements from sample project
    sample_dir = Path(__file__).resolve().parents[2] / "sample_project"
    req_file = sample_dir / "requirements.md"
    assert req_file.exists(), f"requirements.md not found at {req_file}"

    project_id = uuid.uuid4()
    reqs = RequirementExtractor.extract_from_text(
        req_file.read_text(encoding="utf-8"),
        project_id=project_id,
        source_name="requirements.md",
    )
    assert len(reqs) >= 1

    calc_req = next((r for r in reqs if "CALC" in r.identifier), None)
    assert calc_req is not None, "REQ-CALC-01 requirement not found"
    assert len(calc_req.acceptance_criteria) >= 2

    # 2. Construct system model with count_items entity
    calc_py = sample_dir / "app" / "calculator.py"
    assert calc_py.exists()

    req_dicts = [
        {
            "id": str(calc_req.id),
            "identifier": calc_req.identifier,
            "title": calc_req.title,
            "description": calc_req.description,
            "acceptance_criteria": calc_req.acceptance_criteria,
        }
    ]

    entities = [
        {
            "id": str(uuid.uuid4()),
            "name": "count_items",
            "file_path": str(calc_py),
            "entity_type": "FUNCTION",
            "parameters": [{"name": "items", "type": "list"}],
            "return_type": "int",
        }
    ]

    system_model = {"entities": entities}

    # 3. Generate requirement verified test cases
    gen = RequirementVerifiedGenerator()
    test_cases = gen.generate(project_id, req_dicts, system_model)
    assert len(test_cases) >= 2, f"Expected at least 2 test cases, got {len(test_cases)}"

    ac1_test = next((tc for tc in test_cases if "ac_1" in tc.name), None)
    assert ac1_test is not None, "ac_1 test case not generated"

    # Verify test code contains real invocation and real assert
    assert "from " in ac1_test.test_code
    assert "count_items(" in ac1_test.test_code
    assert "actual_result ==" in ac1_test.test_code
    assert "['a', 'b', 'c']" in ac1_test.test_code
    assert "== 3" in ac1_test.test_code

    # 4. Now execute the generated test code against the real calculator.py
    # Since calculator.py has the off-by-one bug (return len(items) + 1), it must FAIL!
    import importlib.util
    spec = importlib.util.spec_from_file_location("app.calculator", str(calc_py))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["app.calculator"] = mod
    spec.loader.exec_module(mod)

    # Compile and execute the test function in a sandbox namespace
    exec_globals = {}
    exec(ac1_test.test_code, exec_globals)
    test_func = exec_globals[ac1_test.name]

    # Must raise AssertionError because 3 != 4
    with pytest.raises(AssertionError) as exc_info:
        test_func()

    assert "Expected 3, got 4" in str(exc_info.value)
