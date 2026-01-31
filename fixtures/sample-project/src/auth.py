"""Authentication module with intentional vulnerability."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class User:
    """User model."""
    id: int
    username: str
    email: str
    password_hash: str
    created_at: datetime


# Simulated user database
_users_db: dict[str, User] = {
    "admin": User(
        id=1,
        username="admin",
        email="admin@example.com",
        password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
        created_at=datetime.now(),
    ),
    "testuser": User(
        id=2,
        username="testuser",
        email="test@example.com",
        password_hash=hashlib.sha256("password123".encode()).hexdigest(),
        created_at=datetime.now(),
    ),
}

# Session storage
_sessions: dict[str, tuple[str, datetime]] = {}


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> tuple[bool, str | None]:
    """Authenticate a user with username and password.

    BUG: This function doesn't validate empty passwords!
    An empty password will still pass the hash comparison if the stored
    hash happens to match the hash of an empty string.

    Args:
        username: The username to authenticate
        password: The password to verify

    Returns:
        Tuple of (success, session_token or error_message)
    """
    user = _users_db.get(username)

    if not user:
        return False, "User not found"

    # BUG: No check for empty password!
    password_hash = hash_password(password)

    if password_hash != user.password_hash:
        return False, "Invalid password"

    # Create session
    token = secrets.token_hex(32)
    _sessions[token] = (username, datetime.now() + timedelta(hours=24))

    return True, token


def verify_session(token: str) -> User | None:
    """Verify a session token and return the user.

    Args:
        token: The session token to verify

    Returns:
        User if valid session, None otherwise
    """
    if token not in _sessions:
        return None

    username, expires_at = _sessions[token]

    if datetime.now() > expires_at:
        del _sessions[token]
        return None

    return _users_db.get(username)


def logout(token: str) -> bool:
    """Invalidate a session token.

    Args:
        token: The session token to invalidate

    Returns:
        True if session was found and removed, False otherwise
    """
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def get_user_by_username(username: str) -> User | None:
    """Get a user by username.

    Args:
        username: The username to look up

    Returns:
        User if found, None otherwise
    """
    return _users_db.get(username)


def create_user(username: str, email: str, password: str) -> User | None:
    """Create a new user.

    Args:
        username: The username for the new user
        email: The email for the new user
        password: The password for the new user

    Returns:
        The created User, or None if username already exists
    """
    if username in _users_db:
        return None

    user = User(
        id=len(_users_db) + 1,
        username=username,
        email=email,
        password_hash=hash_password(password),
        created_at=datetime.now(),
    )
    _users_db[username] = user
    return user
