# app/routes/auth/forgot_password.py ** NEW

import logging
from fastapi import APIRouter, Form, HTTPException, Request
from app.core.config import settings
from app.core.limiter import limiter
from supabase import create_client

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize the Supabase client with the ANON key (for public operations)
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

@router.post("/forgot-password")
@limiter.limit(settings.RATE_LIMIT_FORGOT_PASSWORD)
async def forgot_password(request: Request, email: str = Form(...)):
    """
    Initiates password reset by sending a password reset email via Supabase Auth.
    """
    logger.info(f"Password reset requested for email: {email}")

    redirect_url = f"{settings.FRONTEND_URL}/reset"
    try:
        response = supabase.auth.reset_password_email(email, redirect_to=redirect_url)
        if response is None:
            logger.info(f"Password reset email sent to: {email}")
            return {"message": "Password reset email sent."}
        else:
            logger.warning(f"Unexpected response from Supabase when resetting password for: {email}")
            raise HTTPException(status_code=400, detail="Failed to send reset email.")
    except Exception as e:
        logger.error(f"Error sending password reset email to {email}: {e}", exc_info=True)
        # Never reveal details to client
        raise HTTPException(status_code=500, detail="Error processing password reset.")

"""
--------------------------------------------------------------------
Purpose:
    Allows users to initiate a password reset via Supabase Auth, sending an email with a reset link.

What It Does:
    - Accepts email via POST form.
    - Calls Supabase Auth API to trigger a password reset email.
    - Uses frontend URL as the redirect after reset.

Used By:
    - `/forgot-password` endpoint (frontend "Forgot your password?" forms).

Good Practice:
    - Uses ANON key for public auth requests.
    - Never leaks sensitive error details to user (prevents info leakage).
    - Logs both requests and errors for troubleshooting.
    - Applies rate limiting to prevent brute-force or spam abuse.

Security & Scalability:
    - Does not reveal whether email exists (prevents enumeration).
    - Rate-limited per IP to prevent spam.
    - Defensively handles unexpected SDK behavior.

--------------------------------------------------------------------
"""
