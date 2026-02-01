"""Tests for the calculator module."""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from calculator import add, subtract, multiply, divide


class TestAdd:
    """Tests for add function."""

    def test_add_positive_numbers(self):
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        assert add(-2, -3) == -5

    def test_add_mixed_numbers(self):
        assert add(-2, 5) == 3

    def test_add_zero(self):
        assert add(0, 5) == 5
        assert add(5, 0) == 5

    def test_add_floats(self):
        assert add(1.5, 2.5) == 4.0


class TestSubtract:
    """Tests for subtract function."""

    def test_subtract_positive(self):
        assert subtract(5, 3) == 2

    def test_subtract_negative_result(self):
        assert subtract(3, 5) == -2

    def test_subtract_zero(self):
        assert subtract(5, 0) == 5


class TestMultiply:
    """Tests for multiply function."""

    def test_multiply_positive(self):
        assert multiply(3, 4) == 12

    def test_multiply_by_zero(self):
        assert multiply(5, 0) == 0

    def test_multiply_negative(self):
        assert multiply(-3, 4) == -12


class TestDivide:
    """Tests for divide function."""

    def test_divide_positive(self):
        assert divide(10, 2) == 5

    def test_divide_float_result(self):
        assert divide(7, 2) == 3.5

    def test_divide_by_one(self):
        assert divide(5, 1) == 5

    def test_divide_by_zero_raises(self):
        """Division by zero should raise ValueError."""
        with pytest.raises(ValueError, match="[Cc]annot divide by zero|[Dd]ivision by zero"):
            divide(10, 0)

    def test_divide_zero_by_number(self):
        assert divide(0, 5) == 0
