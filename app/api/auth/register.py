# app/api/auth/register.py

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, EmailStr, constr
from app.core.config import settings
from app.core.limiter import limiter
from app.services.supabase import supabase  # Your initialized Supabase client

logger = logging.getLogger(__name__)
router = APIRouter()

# Registration request schema with validation
class RegisterRequest(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    first_name: constr(min_length=1)
    last_name: constr(min_length=1)
    username: constr(min_length=8)

@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_LOGIN)  # Rate-limit registrations for abuse protection
async def register_user(request: Request, data: RegisterRequest):
    """
    Registers a new user using Supabase Auth and inserts metadata into public.users.

    The user must verify their email via the magic link sent by Supabase before
    being able to log in.

    Args:
        data (RegisterRequest): Registration details including email, password, first/last name, username.

    Returns:
        JSON response indicating registration success or failure.
    """
    email = data.email.lower().strip()
    password = data.password
    first_name = data.first_name.strip()
    last_name = data.last_name.strip()
    username = data.username.lower().strip()

    logger.info(f"Attempting registration for email: {email}")

    try:
        # Supabase magic link verification redirect URL
        redirect_url = f"{settings.FRONTEND_URL}/verify-email"

        # Call Supabase Auth sign_up without 'options'
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username
                }
            }
        })

        if response.user:
            logger.info(f"User signed up successfully: {email}")

            # Insert user metadata into your public.users table
            user_meta = {
                "id": response.user.id,
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "plan": "free",
            }

            profile_res = supabase.table("users").insert(user_meta).execute()
            if profile_res.status_code != 201:
                logger.warning(f"Failed to insert metadata for user {email}: {profile_res.data}")
            else:
                logger.info(f"Inserted metadata into public.users for user {email}")

            return {"message": "Registration successful. Please check your email to verify your account."}
        else:
            # If user is None, registration failed
            logger.error(f"Registration failed for {email}: {response}")
            raise HTTPException(status_code=400, detail="Registration failed. Possibly user already exists.")

    except Exception as e:
        logger.error(f"Registration error for {email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during registration.")

"""
--------------------------------------------------------------------
Purpose:
    Handles user registration using Supabase Auth with magic-link email verification.

What It Does:
    - Validates incoming registration data.
    - Calls Supabase Auth `sign_up` with email, password, and redirect URL for verification.
    - Inserts user metadata in `public.users` for profile and SaaS info.
    - Logs all key steps and errors.
    - Protects endpoint with rate limiting.

Used By:
    - Frontend registration form.

Good Practice:
    - Do NOT store passwords yourself; rely on Supabase Auth.
    - Require email verification before login.
    - Keep user metadata in a separate table for business logic.
    - Handle and log all exceptions.
    - Use strict input validation and normalization.

Security & Scalability:
    - Passwords never leave Supabase Auth.
    - RLS and policies on `public.users` restrict data access.
    - Rate limiting prevents abuse and brute force.
--------------------------------------------------------------------
"""
