"""Tests for authentication module."""

import pytest

from src.auth import authenticate, create_user, hash_password, logout, verify_session


class TestAuthenticate:
    """Tests for the authenticate function."""

    def test_authenticate_valid_credentials(self):
        """Test authentication with valid credentials."""
        success, token = authenticate("admin", "admin123")
        assert success is True
        assert token is not None
        assert len(token) == 64  # hex token

    def test_authenticate_invalid_password(self):
        """Test authentication with wrong password."""
        success, error = authenticate("admin", "wrongpassword")
        assert success is False
        assert error == "Invalid password"

    def test_authenticate_nonexistent_user(self):
        """Test authentication with non-existent user."""
        success, error = authenticate("nonexistent", "password")
        assert success is False
        assert error == "User not found"

    def test_authenticate_empty_password_rejected(self):
        """Test that empty password is rejected.

        This test will FAIL until the bug is fixed!
        """
        success, result = authenticate("admin", "")
        assert success is False, "Empty password should be rejected"
        assert "empty" in result.lower() or "password" in result.lower()

    def test_authenticate_whitespace_password_rejected(self):
        """Test that whitespace-only password is rejected."""
        success, result = authenticate("admin", "   ")
        assert success is False, "Whitespace password should be rejected"

    def test_authenticate_none_password_rejected(self):
        """Test that None password is handled gracefully."""
        # This should not crash
        try:
            success, result = authenticate("admin", None)
            assert success is False
        except TypeError:
            pytest.fail("Should handle None password gracefully")


class TestSession:
    """Tests for session management."""

    def test_verify_valid_session(self):
        """Test verifying a valid session token."""
        success, token = authenticate("admin", "admin123")
        assert success

        user = verify_session(token)
        assert user is not None
        assert user.username == "admin"

    def test_verify_invalid_session(self):
        """Test verifying an invalid session token."""
        user = verify_session("invalid_token")
        assert user is None

    def test_logout_valid_session(self):
        """Test logging out with valid session."""
        success, token = authenticate("admin", "admin123")
        assert success

        result = logout(token)
        assert result is True

        # Session should be invalid now
        user = verify_session(token)
        assert user is None

    def test_logout_invalid_session(self):
        """Test logging out with invalid session."""
        result = logout("invalid_token")
        assert result is False


class TestCreateUser:
    """Tests for user creation."""

    def test_create_user_success(self):
        """Test creating a new user."""
        user = create_user("newuser", "new@example.com", "password123")
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"

    def test_create_user_duplicate_username(self):
        """Test creating user with existing username."""
        user = create_user("admin", "admin2@example.com", "password")
        assert user is None  # Should fail, username exists


class TestHashPassword:
    """Tests for password hashing."""

    def test_hash_password_consistency(self):
        """Test that same password produces same hash."""
        hash1 = hash_password("test123")
        hash2 = hash_password("test123")
        assert hash1 == hash2

    def test_hash_password_different_passwords(self):
        """Test that different passwords produce different hashes."""
        hash1 = hash_password("test123")
        hash2 = hash_password("test456")
        assert hash1 != hash2
