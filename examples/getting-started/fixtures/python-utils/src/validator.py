"""Input validation utilities."""


def is_positive(value: float) -> bool:
    """Check if a number is positive.

    Args:
        value: Number to check

    Returns:
        True if value is greater than zero
    """
    return value > 0


def is_in_range(value: float, min_val: float, max_val: float) -> bool:
    """Check if a value is within a range (inclusive).

    Args:
        value: Number to check
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if min_val <= value <= max_val
    """
    return min_val <= value <= max_val


def is_valid_username(username: str) -> bool:
    """Check if a username is valid.

    Valid usernames:
    - 3-20 characters long
    - Only alphanumeric and underscores
    - Must start with a letter

    Args:
        username: Username to validate

    Returns:
        True if username is valid
    """
    if not username or len(username) < 3 or len(username) > 20:
        return False

    if not username[0].isalpha():
        return False

    return all(c.isalnum() or c == "_" for c in username)


# TODO: Add email validation function
# def is_valid_email(email: str) -> bool:
#     """Check if an email address is valid."""
#     pass
