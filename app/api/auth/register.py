# app/api/auth/register.py

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, constr
from app.core.config import settings
from app.core.limiter import limiter
from supabase import create_client

from app.utils.validators import (
    is_valid_username,
    is_strong_password,
    normalize_username,
    normalize_email,
)

logger = logging.getLogger(__name__)
router = APIRouter()
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    first_name: constr(strip_whitespace=True, min_length=1, max_length=50)
    last_name: constr(strip_whitespace=True, min_length=1, max_length=50)
    username: constr(strip_whitespace=True, min_length=8, max_length=32)

@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def register_user(request: Request, data: RegisterRequest):
    """
    Registers a new user with Supabase Auth and syncs metadata to `public.users` via DB trigger.
    ---
    - Validates strong password, username, and email.
    - No manual insert to `public.users`; handled by DB trigger.
    - User must click magic link in email to activate account.
    """
    email = normalize_email(data.email)
    password = data.password
    first_name = data.first_name.strip()
    last_name = data.last_name.strip()
    username = normalize_username(data.username)

    logger.info(f"Attempting registration for email: {email}")

    # --- Custom Validations ---
    if not is_valid_username(username):
        logger.warning(f"Rejected registration: invalid username '{username}'")
        raise HTTPException(status_code=400, detail="Invalid username. Must be ≥8 chars, letters/numbers.")

    if not is_strong_password(password):
        logger.warning(f"Rejected registration for {email}: weak password")
        raise HTTPException(status_code=400, detail="Password too weak. Must have upper, lower, digit, special char.")

    # (Optional) Check for disallowed usernames, reserved words, etc.

    try:
        # Supabase Auth signup with user_metadata (will trigger DB sync)
        response = supabase.auth.sign_up(
            {"email": email, "password": password},
            user_metadata={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            }
        )
        logger.info(f"User signed up successfully: {email}")
    except Exception as e:
        logger.error(f"Registration error for {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during registration.")

    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": email,
        "username": username
    }

"""
---------------------------------------------------------------------
✅ Purpose:
    Registers a new user using Supabase Auth. All user data is written to
    Supabase Auth (authentication) and metadata is copied to `public.users`
    via a DB trigger—no direct insert needed here.

🔍 What It Does:
    - Validates all fields and password strength.
    - Calls Supabase Auth signup (with email, password, metadata).
    - Does NOT manually insert into public.users table.
    - Relies on DB trigger for metadata sync.
    - User must verify via magic link to activate account.

📌 Used By:
    - `/register` API (frontend registration form)
    - Onboarding and user creation

🧠 Good Practice:
    - All sensitive errors are only logged, not sent to user.
    - Rate limit endpoint to prevent abuse.
    - Usernames and emails always normalized (lowercase, no spaces).
    - All validation (passwords, usernames) is strict.

🔒 Security & Scalability:
    - Never stores or logs plaintext passwords.
    - All account actions audited with logging.
    - Only returns generic errors to clients for security.

---------------------------------------------------------------------
"""
