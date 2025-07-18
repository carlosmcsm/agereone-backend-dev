# app/api/auth/update_key.py ** NEW

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, constr
from app.deps.supabase_auth import get_current_user
from app.services.supabase import upsert_openai_key_and_model
from app.core.limiter import limiter
from app.core.config import settings
from pydantic import validator

logger = logging.getLogger(__name__)
router = APIRouter()

# You may want to restrict to models supported by your SaaS
ALLOWED_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4o",
    "gpt-4",
    "gpt-4-turbo",
    # Add/remove as needed
]

class OpenAIKeyUpdateRequest(BaseModel):
    api_key: constr(min_length=40, max_length=100)  # Basic length check for OpenAI keys
    model: str

    # Optionally enforce allowed models (if using dropdown in UI)
    @validator("model")
    def validate_model(cls, value):
        if value not in ALLOWED_MODELS:
            raise ValueError(f"Model {value} is not supported.")
        return value

@router.post("/update-key")
@limiter.limit(settings.RATE_LIMIT_UPDATE_KEY)
async def update_openai_key(
    request: Request,
    data: OpenAIKeyUpdateRequest,
    user=Depends(get_current_user)
):
    """
    Stores or updates the user's OpenAI API key and preferred model.
    """
    user_id = user["user_id"]
    logger.info(f"User {user_id} updating OpenAI API key/model.")

    # Validate model
    if data.model not in ALLOWED_MODELS:
        logger.warning(f"Model {data.model} is not allowed for user {user_id}")
        raise HTTPException(status_code=400, detail="Model is not supported.")

    try:
        upsert_openai_key_and_model(user_id, data.api_key, data.model)
        logger.info(f"OpenAI API key/model updated for user {user_id}")
        return {"message": "Key updated successfully."}
    except Exception as e:
        logger.error(f"Failed to update OpenAI key/model for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update OpenAI key/model.")

"""
--------------------------------------------------------------------
Purpose:
    Allows users to store or update their OpenAI API key and preferred model.
    Ensures the key is available for embedding and chat endpoints.

What It Does:
    - Validates and stores (or updates) the user's OpenAI API key and model.
    - Checks that the selected model is allowed by your business logic.
    - Uses service-layer helper for upsert (safe for first-time or repeat calls).
    - Returns a clear success or error message.

Used By:
    - Dashboard "Settings" page (OpenAI API Key & Model entry)
    - Any logic needing to update key/model (user-initiated or admin tools)

Good Practice:
    - Never logs or exposes actual API keys (just that an update occurred).
    - Restricts models to those supported (sync this with your frontend dropdown).
    - Rate-limits to prevent abuse.

Security & Scalability:
    - Keys stored securely in DB, never exposed to other users.
    - Designed for future extension (per-plan model gating, key validation, etc).

--------------------------------------------------------------------
"""
