# app/routes/auth/login.py ** NEW

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from supabase import create_client
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login_user(request: Request):
    """
    Authenticates a user using Supabase Auth (email/password).
    Returns access and refresh tokens if successful, along with the username.
    """
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        logger.info(f"Login attempt for email: {email}")

        # Validate inputs
        if not email or not password:
            logger.warning(f"Missing email or password in login request: {data}")
            raise HTTPException(status_code=400, detail="Email and password required.")

        # Authenticate with Supabase Auth
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})

        # If authentication fails, Supabase returns user=None
        if response.user is None:
            logger.warning(f"Invalid credentials for email: {email}")
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        user_id = response.user.id

        # Fetch the username from your custom users table
        user_response = supabase.table("users").select("username").eq("id", user_id).single().execute()
        if not user_response.data or "username" not in user_response.data:
            logger.error(f"Username not found for user_id: {user_id}")
            raise HTTPException(status_code=404, detail="Username not found.")

        logger.info(f"Login successful for email: {email} (username: {user_response.data['username']})")

        return JSONResponse({
            "username": user_response.data["username"],
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "expires_in": response.session.expires_in,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for email: {email if 'email' in locals() else 'unknown'}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed.")

"""
--------------------------------------------------------------------
Purpose:
    Authenticates users via email and password using Supabase Auth, and retrieves the user's username from the custom users table.

What It Does:
    - Accepts email/password in POST body (JSON).
    - Calls Supabase Auth to sign in.
    - On success, looks up the user's username (for dashboard/profile use).
    - Returns the username and token info in a JSON response.

Used By:
    - `/login` endpoint for the frontend login form.

Good Practice:
    - Always use the ANON key for public client auth requests.
    - Use rate limiting to protect against brute-force attacks.
    - Respond generically on auth errors to avoid information leakage.
    - Never return password or sensitive details.

Security & Scalability:
    - Throttles login attempts to mitigate abuse.
    - Does NOT reveal which part (email or password) was wrong.
    - Logs both success and failure for auditing and security monitoring.
    - Does NOT leak internal exception details.

--------------------------------------------------------------------
"""
