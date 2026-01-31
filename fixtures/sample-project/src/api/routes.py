"""API routes with intentional bugs."""

from flask import Flask, jsonify, request

from src.auth import (
    authenticate,
    create_user,
    get_user_by_username,
    logout,
    verify_session,
)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.route("/api/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy"})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        """Login endpoint.

        Expected JSON body:
        - username: string
        - password: string

        Returns:
            JSON with token on success, error on failure
        """
        data = request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")

        success, result = authenticate(username, password)

        if success:
            return jsonify({"token": result})
        else:
            return jsonify({"error": result}), 401

    @app.route("/api/auth/logout", methods=["POST"])
    def logout_route():
        """Logout endpoint.

        Requires Authorization header with Bearer token.
        """
        token = _get_token_from_header()
        if not token:
            return jsonify({"error": "Missing authorization"}), 401

        if logout(token):
            return jsonify({"message": "Logged out"})
        else:
            return jsonify({"error": "Invalid session"}), 401

    @app.route("/api/profile", methods=["GET"])
    def get_profile():
        """Get current user's profile.

        BUG: Doesn't handle null user object!

        Requires Authorization header with Bearer token.
        """
        token = _get_token_from_header()
        if not token:
            return jsonify({"error": "Missing authorization"}), 401

        user = verify_session(token)

        # BUG: No null check for user! Will crash if session is invalid
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        })

    @app.route("/api/users", methods=["GET"])
    def list_users():
        """List all users.

        TODO: Add pagination support
        Currently returns all users which doesn't scale.
        """
        # This is a stub - in real app would query database
        # For now just return a sample list
        users = [
            {"id": 1, "username": "admin", "email": "admin@example.com"},
            {"id": 2, "username": "testuser", "email": "test@example.com"},
        ]
        return jsonify(users)

    @app.route("/api/users", methods=["POST"])
    def create_user_route():
        """Create a new user.

        TODO: Add input validation

        Expected JSON body:
        - username: string
        - email: string
        - password: string
        """
        data = request.get_json()

        # TODO: Validate input (email format, password strength, username format)
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")

        user = create_user(username, email, password)

        if user:
            return jsonify({
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }), 201
        else:
            return jsonify({"error": "Username already exists"}), 409

    @app.route("/api/users/<username>", methods=["GET"])
    def get_user(username: str):
        """Get a user by username.

        Args:
            username: The username to look up
        """
        user = get_user_by_username(username)

        if user:
            return jsonify({
                "id": user.id,
                "username": user.username,
                "email": user.email,
            })
        else:
            return jsonify({"error": "User not found"}), 404

    def _get_token_from_header() -> str | None:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    return app


# Create default app instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
