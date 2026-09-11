"""
Deliberately failing test designed to trigger defect triage and failure root cause analysis.
"""

def test_boundary_calculation_defect():
    """
    Planted defect: asserts 1 == 2 to generate a genuine Failure execution.
    """
    expected = 2
    actual = 1
    assert actual == expected, "Intentional failure: assertion 1 == 2 defect"
