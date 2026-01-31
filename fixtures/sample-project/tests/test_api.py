"""Tests for API routes."""

import pytest

from src.api.routes import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Get an authentication token."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    return response.get_json()["token"]


class TestHealth:
    """Tests for health endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "healthy"


class TestAuth:
    """Tests for authentication endpoints."""

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        assert "token" in response.get_json()

    def test_login_invalid_password(self, client):
        """Test login with invalid password."""
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert response.status_code == 401
        assert "error" in response.get_json()

    def test_logout_success(self, client, auth_token):
        """Test successful logout."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200


class TestProfile:
    """Tests for profile endpoint."""

    def test_profile_success(self, client, auth_token):
        """Test getting profile with valid token."""
        response = client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "admin"

    def test_profile_no_auth(self, client):
        """Test getting profile without authentication."""
        response = client.get("/api/profile")
        assert response.status_code == 401

    def test_profile_null_user(self, client):
        """Test profile with invalid/expired token.

        This test will FAIL until the null user bug is fixed!
        The endpoint should return 401, not crash.
        """
        response = client.get(
            "/api/profile",
            headers={"Authorization": "Bearer invalid_token_12345"},
        )
        # Should return 401, not 500 (crash)
        assert response.status_code == 401, "Should return 401 for invalid session"
        data = response.get_json()
        assert "error" in data


class TestUsers:
    """Tests for user endpoints."""

    def test_list_users(self, client):
        """Test listing users."""
        response = client.get("/api/users")
        assert response.status_code == 200
        users = response.get_json()
        assert isinstance(users, list)
        assert len(users) >= 1

    def test_get_user_exists(self, client):
        """Test getting existing user."""
        response = client.get("/api/users/admin")
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "admin"

    def test_get_user_not_found(self, client):
        """Test getting non-existent user."""
        response = client.get("/api/users/nonexistent")
        assert response.status_code == 404

    def test_create_user_success(self, client):
        """Test creating a new user."""
        response = client.post(
            "/api/users",
            json={
                "username": "newuser123",
                "email": "newuser@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["username"] == "newuser123"


class TestUserValidation:
    """Tests for user input validation.

    These tests will FAIL until validation is implemented!
    """

    def test_user_validation_invalid_email(self, client):
        """Test that invalid email is rejected."""
        response = client.post(
            "/api/users",
            json={
                "username": "validuser",
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert response.status_code == 400, "Should reject invalid email"
        data = response.get_json()
        assert "error" in data or "errors" in data

    def test_user_validation_short_password(self, client):
        """Test that short password is rejected."""
        response = client.post(
            "/api/users",
            json={
                "username": "validuser2",
                "email": "valid@example.com",
                "password": "short",  # Less than 8 characters
            },
        )
        assert response.status_code == 400, "Should reject short password"

    def test_user_validation_password_no_number(self, client):
        """Test that password without number is rejected."""
        response = client.post(
            "/api/users",
            json={
                "username": "validuser3",
                "email": "valid@example.com",
                "password": "password",  # No number
            },
        )
        assert response.status_code == 400, "Should reject password without number"

    def test_user_validation_invalid_username(self, client):
        """Test that invalid username is rejected."""
        response = client.post(
            "/api/users",
            json={
                "username": "ab",  # Too short (less than 3 chars)
                "email": "valid@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400, "Should reject short username"

    def test_user_validation_username_special_chars(self, client):
        """Test that username with special chars is rejected."""
        response = client.post(
            "/api/users",
            json={
                "username": "user@name!",  # Special characters
                "email": "valid@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400, "Should reject username with special chars"


class TestPagination:
    """Tests for pagination.

    These tests will FAIL until pagination is implemented!
    """

    def test_pagination_default(self, client):
        """Test default pagination."""
        response = client.get("/api/users")
        assert response.status_code == 200
        data = response.get_json()

        # Should have pagination metadata
        assert "data" in data, "Response should have 'data' field"
        assert "total" in data, "Response should have 'total' field"
        assert "page" in data, "Response should have 'page' field"
        assert "per_page" in data, "Response should have 'per_page' field"

    def test_pagination_custom_page(self, client):
        """Test custom page parameter."""
        response = client.get("/api/users?page=2&per_page=5")
        assert response.status_code == 200
        data = response.get_json()
        assert data["page"] == 2
        assert data["per_page"] == 5

    def test_pagination_metadata(self, client):
        """Test pagination metadata is correct."""
        response = client.get("/api/users?page=1&per_page=1")
        assert response.status_code == 200
        data = response.get_json()

        # Should calculate pages correctly
        assert "pages" in data
        if data["total"] > 0:
            expected_pages = (data["total"] + data["per_page"] - 1) // data["per_page"]
            assert data["pages"] == expected_pages
