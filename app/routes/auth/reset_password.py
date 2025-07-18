# app/routes/auth/reset_password.py ** NEW

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from supabase import create_client
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

@router.post("/reset-password")
@limiter.limit(settings.RATE_LIMIT_RESET_PASSWORD)
async def reset_password(request: Request):
    """
    Completes password reset using the Supabase recovery token and new password.

    Expects JSON with:
      - token: Supabase recovery token (from the email)
      - password: new password

    Returns:
      - JSON status message
    """
    try:
        data = await request.json()
        token = data.get("token")
        new_password = data.get("password")

        logger.info("Password reset attempt received.")

        if not token or not new_password:
            logger.warning("Reset attempt with missing token or password.")
            raise HTTPException(status_code=400, detail="Token and new password are required.")

        response = supabase.auth.update_user(access_token=token, password=new_password)
        if response.user is None:
            logger.warning("Password reset failed—invalid or expired token.")
            raise HTTPException(status_code=400, detail="Password reset failed.")

        logger.info("Password reset successful for a user.")
        return JSONResponse({"status": "Password reset successful."})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Internal error during password reset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")

"""
--------------------------------------------------------------------
Purpose:
    Completes the password reset for a user using the Supabase recovery token.

What It Does:
    - Accepts a POST with JSON containing `token` (from reset email) and `password`.
    - Calls Supabase Auth API to update the password for the user associated with that token.
    - Returns a generic success or failure message.

Used By:
    - `/reset-password` endpoint (frontend password reset forms).

Good Practice:
    - Rate limits the endpoint (to 5/hour/IP by default).
    - Never leaks sensitive error messages to clients.
    - Always validates both token and password are present.

Security & Scalability:
    - Responds generically to avoid revealing user existence.
    - Logs both successful and failed reset attempts.
    - Limits the number of reset attempts per IP.

--------------------------------------------------------------------
"""
