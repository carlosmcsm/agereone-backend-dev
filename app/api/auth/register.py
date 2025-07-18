# app/api/auth/register.py

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from app.core.config import settings
from app.utils.validators import is_valid_username, is_strong_password
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    username: str

@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register_user(request: Request, req: RegisterRequest):
    """
    Registers a new user in both Supabase Auth and your own users table.
    - Enforces username and password policy.
    - Syncs user_id between Auth and DB.
    - Sends invite/magic link email.

    Returns:
        JSON: { message, subdomain }
    """
    username = req.username.lower()
    email = req.email.lower()
    logger.info(f"Attempting registration for email: {email}")

    # 1. Username validity (≥8 chars, only letters/numbers, at least one letter)
    if not is_valid_username(username):
        logger.warning(f"Invalid username attempted: {username}")
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 8 characters, only letters and numbers, and contain at least one letter.",
        )

    # 2. Password strength
    if not is_strong_password(req.password):
        logger.warning(f"Weak password for email: {email}")
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters, with uppercase, lowercase, a number, and a special character."
        )

    # 3. Email uniqueness (case-insensitive)
    user_check = supabase.table("users").select("id").eq("email", email).maybe_single().execute()
    if user_check and getattr(user_check, "data", None):
        logger.warning(f"Registration failed: Email already exists: {email}")
        raise HTTPException(status_code=400, detail="Email already exists.")

    # 4. Username uniqueness
    username_check = supabase.table("users").select("id").eq("username", username).maybe_single().execute()
    if username_check and getattr(username_check, "data", None):
        logger.warning(f"Registration failed: Username already exists: {username}")
        raise HTTPException(status_code=400, detail="Username already exists.")

    # 5. Create user in Supabase Auth (Admin API)
    try:
        auth_res = supabase.auth.admin.create_user({
            "email": email,
            "password": req.password,
            "email_confirm": False
        })
    except Exception as e:
        logger.error(f"Auth user creation exception for {email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Auth user.")

    user_obj = getattr(auth_res, "user", None)
    if not user_obj:
        detail = getattr(auth_res, "error", None)
        logger.error(f"Auth user creation error for {email}: {detail}")
        raise HTTPException(status_code=500, detail="Auth user creation failed.")
    user_id = str(user_obj.id)
    logger.info(f"Created Auth user_id {user_id} for email {email}")

    # 6. Insert into your users table
    try:
        db_res = supabase.table("users").insert({
            "id": user_id,
            "email": email,
            "first_name": req.first_name,
            "last_name": req.last_name,
            "username": username,
            "plan": "free",
            "profile_uploaded": False
        }).execute()
    except Exception as e:
        logger.error(f"DB insert exception for user {email}: {e}")
        raise HTTPException(status_code=500, detail="Could not insert user metadata.")

    if db_res is None or getattr(db_res, "error", None):
        msg = getattr(db_res.error, "message", None) if db_res and db_res.error else "Could not insert user metadata."
        logger.error(f"DB insert error for user {email}: {msg}")
        raise HTTPException(status_code=500, detail=msg)

    # 7. Send invite/magic link email (does not block registration)
    try:
        invite_res = supabase.auth.admin.invite_user_by_email(email)
        if hasattr(invite_res, "error") and invite_res.error:
            logger.warning(f"Magic link sending failed for {email}: {invite_res.error}")
    except Exception as e:
        logger.warning(f"Failed to send magic link for {email}: {e}")

    logger.info(f"User registered successfully: {email}")

    return {
        "message": "User registered successfully. Please check your email for the confirmation link.",
        "subdomain": f"{username}.agereone.com"
    }

"""
-------------------------------------------------------------------------------
✅ Purpose:
    Handles full registration flow for new users (API, dashboard, onboarding).

🔍 What It Does:
    - Validates username, password, and checks for unique email/username.
    - Creates user in Supabase Auth (secure, backend only).
    - Inserts metadata in your own users table (syncs with Auth user_id).
    - Sends magic link (invite) for email confirmation (does not block user creation).

📌 Used By:
    - SaaS dashboard and API for public signups.
    - Admin onboarding flows.

🧠 Best Practices:
    - Use the SERVICE_ROLE_KEY for backend-only admin API access.
    - Rate limit to prevent abuse (see @limiter).
    - Never return internal errors to users (log them server-side).
    - Always mask/exclude passwords and sensitive fields from responses.
    - Magic link/email delivery failures are logged but do not block signup.

🔒 Security:
    - All sensitive actions (user creation, metadata insert) are backend only.
    - No API key or password is ever exposed in logs.
    - No row is created in your users table without successful Auth registration.

🚦 Extensibility:
    - Easily add additional fields (plan, referral, etc).
    - Add custom onboarding (welcome emails, analytics, etc).

-------------------------------------------------------------------------------
"""
