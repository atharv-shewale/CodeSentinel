"""
Calculator and arithmetic processing utilities.
"""

def add(a: int, b: int) -> int:
    """Sum two numbers."""
    return a + b


def divide(a: float, b: float) -> float:
    """Divide a by b with zero division protection."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def count_items(items: list) -> int:
    """
    Count the number of items in a batch.
    Defect: Obvious off-by-one bug (+ 1) contradicting REQ-CALC-01.
    """
    return len(items) + 1

