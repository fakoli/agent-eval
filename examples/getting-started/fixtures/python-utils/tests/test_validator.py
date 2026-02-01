"""Tests for the validator module."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator import is_positive, is_in_range, is_valid_username


class TestIsPositive:
    """Tests for is_positive function."""

    def test_positive_number(self):
        assert is_positive(5) is True

    def test_negative_number(self):
        assert is_positive(-5) is False

    def test_zero(self):
        assert is_positive(0) is False

    def test_small_positive(self):
        assert is_positive(0.001) is True


class TestIsInRange:
    """Tests for is_in_range function."""

    def test_in_range(self):
        assert is_in_range(5, 1, 10) is True

    def test_at_min(self):
        assert is_in_range(1, 1, 10) is True

    def test_at_max(self):
        assert is_in_range(10, 1, 10) is True

    def test_below_range(self):
        assert is_in_range(0, 1, 10) is False

    def test_above_range(self):
        assert is_in_range(11, 1, 10) is False


class TestIsValidUsername:
    """Tests for is_valid_username function."""

    def test_valid_username(self):
        assert is_valid_username("john_doe") is True

    def test_valid_username_with_numbers(self):
        assert is_valid_username("user123") is True

    def test_too_short(self):
        assert is_valid_username("ab") is False

    def test_too_long(self):
        assert is_valid_username("a" * 21) is False

    def test_starts_with_number(self):
        assert is_valid_username("123user") is False

    def test_invalid_characters(self):
        assert is_valid_username("user@name") is False

    def test_empty_string(self):
        assert is_valid_username("") is False


class TestIsValidEmail:
    """Tests for is_valid_email function (to be implemented)."""

    def test_valid_email(self):
        """Test valid email addresses."""
        from validator import is_valid_email

        assert is_valid_email("user@example.com") is True
        assert is_valid_email("test.user@domain.org") is True
        assert is_valid_email("name+tag@company.co.uk") is True

    def test_invalid_email_no_at(self):
        """Email must contain @ symbol."""
        from validator import is_valid_email

        assert is_valid_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        """Email must have a domain."""
        from validator import is_valid_email

        assert is_valid_email("user@") is False

    def test_invalid_email_empty(self):
        """Empty string is not valid."""
        from validator import is_valid_email

        assert is_valid_email("") is False
