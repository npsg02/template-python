"""Shared validation utilities."""

import re
from typing import Any, Optional, Pattern

# Common validation patterns
EMAIL_PATTERN: Pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
UUID_PATTERN: Pattern = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if email format is valid, False otherwise
    """
    return bool(EMAIL_PATTERN.match(email))


def validate_uuid(uuid: str) -> bool:
    """Validate UUID format.

    Args:
        uuid: UUID string to validate

    Returns:
        bool: True if UUID format is valid, False otherwise
    """
    return bool(UUID_PATTERN.match(uuid.lower()))


def validate_required_fields(
    data: dict[str, Any], required_fields: list[str]
) -> tuple[bool, Optional[str]]:
    """Validate required fields in a dictionary.

    Args:
        data: Dictionary containing data to validate
        required_fields: List of required field names

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, None
