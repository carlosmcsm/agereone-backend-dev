# app/utils/validators.py

import re
import logging

logger = logging.getLogger(__name__)

USERNAME_REGEX = r"^[a-zA-Z0-9]{8,}$"

def is_valid_username(username: str) -> bool:
    """
    Checks if the username is valid:
    - At least 8 characters
    - Letters and numbers only
    - At least one letter present
    """
    username = (username or "").lower()
    valid = (
        bool(re.fullmatch(r'[A-Za-z0-9]{8,}', username))
        and re.search(r'[A-Za-z]', username) is not None
    )
    if not valid:
        logger.debug(f"Username validation failed: '{username}'")
    return valid

def is_valid_email(email: str) -> bool:
    """
    Basic email format check.
    - Only validates pattern: local@domain.tld
    - Does NOT check deliverability or advanced syntax
    """
    valid = bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email or ""))
    if not valid:
        logger.debug(f"Email validation failed: '{email}'")
    return valid

def normalize_username(username: str) -> str:
    """Lowercases and strips input for consistent username handling."""
    normalized = (username or "").lower().strip()
    logger.debug(f"Normalized username: '{username}' -> '{normalized}'")
    return normalized

def normalize_email(email: str) -> str:
    """Lowercases and strips input for consistent email handling."""
    normalized = (email or "").lower().strip()
    logger.debug(f"Normalized email: '{email}' -> '{normalized}'")
    return normalized

def is_strong_password(password: str) -> bool:
    """
    Password strength policy:
    - At least 8 characters
    - One uppercase, one lowercase, one digit, one special character
    """
    valid = bool(
        re.fullmatch(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$', password or "")
    )
    if not valid:
        logger.debug("Password failed strength validation.")
    return valid

"""
----------------------------------------------------------
Purpose:
    Validation utilities for usernames, emails, and passwords.

What It Does:
    - Checks username and password complexity for registration.
    - Provides normalization for usernames and emails (case-insensitive, trimmed).
    - Validates basic email structure.

Used By:
    - User registration and login flows (backend API).
    - Any endpoint requiring strict credential validation.

Good Practices:
    - Centralize regex-based checks (easy to update policy).
    - Avoid over-validating emails—do not reject valid but rare addresses.
    - Always normalize usernames and emails before DB storage/checks.

Security & Scalability:
    - Ensures password policies for strong credentials.
    - Defends against basic input tampering and common enumeration attacks.
    - Regex limits avoid accidental DoS from catastrophic backtracking.

----------------------------------------------------------
"""
