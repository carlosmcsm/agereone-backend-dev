# app/services/user_metadata.py ** NEW

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from supabase import create_client, Client
from app.core.config import settings
from app.deps.supabase_auth import get_current_user
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

class UserMetadataResponse(BaseModel):
    user: dict
    openai: dict | None = None

@router.get("/user-metadata", response_model=UserMetadataResponse)
def get_user_metadata(
    username: str = Query(..., min_length=8),
    user=Depends(get_current_user)
):
    logger.info(f"User {user.get('username')} requests metadata for username={username}")

    # Enforce user is only accessing their own metadata
    if user.get("username", "").lower() != username.lower():
        logger.warning(f"Unauthorized metadata access attempt by user={user.get('username')} for username={username}")
        raise HTTPException(status_code=403, detail="Unauthorized.")

    user_res = supabase.table("users").select("*").eq("username", username.lower()).single().execute()
    if not user_res or not user_res.data:
        logger.warning(f"User {username} not found in Supabase lookup")
        raise HTTPException(status_code=404, detail="User not found.")
    user_id = user_res.data["id"]

    key_res = supabase.table("openai_keys").select("model").eq("user_id", user_id).single().execute()
    openai_info = key_res.data if key_res and key_res.data else None

    logger.info(f"Successfully returned metadata for user={username} (user_id={user_id})")
    return {
        "user": user_res.data,
        "openai": openai_info
    }

"""
✅ Purpose
Securely retrieve a user's own profile and LLM configuration metadata from Supabase.
Prevents information disclosure—user can only fetch their own data.

🔐 What It Does:
- Looks up a user by username (case-insensitive).
- Checks if the authenticated user's username matches the requested one.
- Retrieves user profile info and LLM model from Supabase (but never the sensitive OpenAI API key itself).
- Returns combined info for dashboard or onboarding population.

📌 Used By:
- Frontend dashboard (prefilling user profile and LLM settings).
- Any secure client-side view that must show current user profile/configuration.

🧠 Good Practice
- Always protect this route with user authentication and ownership check.
- Never leak sensitive API keys to the client.
- Use a Pydantic response model for clear OpenAPI docs and testability.
- Log all important events for audit/debug.
"""
