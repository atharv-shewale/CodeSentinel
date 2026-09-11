"""
Unit tests for calculator module.
"""

import pytest
from app.calculator import add, divide

def test_add_positive_numbers():
    assert add(2, 3) == 5

def test_divide_valid():
    assert divide(10.0, 2.0) == 5.0

def test_divide_zero_raises():
    with pytest.raises(ValueError):
        divide(5.0, 0.0)
