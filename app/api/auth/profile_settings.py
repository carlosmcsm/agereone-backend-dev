# app/api/auth/profile_settings.py ** NEW

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from app.deps.supabase_auth import get_current_user
from app.services.supabase import (
    get_user_by_id,
    get_user_profile_history,
    get_openai_key_and_model_for_user
)
from app.services.user_metadata import get_user_metadata
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

class UserMetadataResponse(BaseModel):
    user: dict
    openai: dict | None = None

@router.get("/user-metadata", response_model=UserMetadataResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def user_metadata(
    request: Request,
    username: str = Query(..., min_length=8),
    user=Depends(get_current_user)
):
    """
    Returns the user's metadata and OpenAI LLM info (never the API key).
    Auth-required: user can only fetch their own metadata.
    """
    logger.info(f"User {user.get('username')} requests metadata for username={username}")

    if user.get("username", "").lower() != username.lower():
        logger.warning(f"Unauthorized metadata access attempt by user={user.get('username')} for username={username}")
        raise HTTPException(status_code=403, detail="Unauthorized.")

    meta = get_user_metadata(username)
    if not meta:
        logger.warning(f"User {username} not found in Supabase lookup")
        raise HTTPException(status_code=404, detail="User not found.")

    logger.info(f"Successfully returned metadata for user={username}")
    return meta

@router.get("/profile-settings")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def profile_settings(request: Request, user=Depends(get_current_user)):
    """
    Returns all user account and profile settings for dashboard display.
    Includes:
    - Profile upload history (filename, created, active)
    - OpenAI key/model (masked)
    - User info, plan, and subdomain
    Protected by authentication and rate limiting.
    """
    user_id = user["user_id"]
    logger.info(f"Profile settings requested by user_id={user_id}")

    try:
        user_data = get_user_by_id(user_id)
        if not user_data:
            logger.error(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found.")

        # Account info
        username = user_data["username"]
        email = user_data["email"]
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        plan = user_data.get("plan", "free")
        subdomain = user_data.get("subdomain")
        profile_uploaded = user_data.get("profile_uploaded", False)

        # Profile uploads history (filenames, upload times, is_active)
        uploads = get_user_profile_history(user_id) or []
        for upload in uploads:
            upload.pop("user_id", None)

        # OpenAI API key (masked) and model
        api_key, model = get_openai_key_and_model_for_user(user_id)
        masked_key = api_key[:6] + "..." + api_key[-4:] if api_key else None

        logger.info(f"Returning profile settings for user_id={user_id} (uploads={len(uploads)})")

        return {
            "user": {
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "plan": plan,
                "subdomain": subdomain,
                "profile_uploaded": profile_uploaded,
            },
            "openai": {
                "api_key": masked_key,
                "model": model
            },
            "uploads": uploads
        }

    except Exception as e:
        logger.error(f"Error getting profile settings for user_id={user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching profile settings.")

"""
--------------------------------------------------------------------
Purpose:
    Supplies all user and profile settings for the dashboard/settings page after login.
    Also exposes a 'user-metadata' endpoint for secure LLM config/user info fetch.

What It Does:
    - Returns user account info, OpenAI config, and profile upload history.
    - Auth and rate limit on all endpoints.
    - Used by frontend for dashboard, settings, onboarding, etc.

Security & Scalability:
    - Never leaks OpenAI key.
    - All logic in service layer, not routes.
    - Easy to extend for usage stats, analytics, or plan features.

--------------------------------------------------------------------
"""
