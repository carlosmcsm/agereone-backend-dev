# app/routes/profile/delete.py ** New

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.deps.supabase_auth import get_current_user
from app.services.supabase import soft_delete_active_profile
from app.services.vectorstore import delete_user_vectors
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.delete("/delete")
@limiter.limit(settings.RATE_LIMIT_DELETE_PROFILE)
async def delete_profile(
    request: Request,
    user=Depends(get_current_user),
):
    """
    Soft deletes the active career profile for the user.
    - Sets is_active = False in Supabase.
    - Deletes all vectors for user in Qdrant.
    """
    user_id = user["user_id"]
    logger.info(f"User {user_id} requested profile delete.")

    try:
        # Soft delete active profile (Supabase)
        rows_deleted = soft_delete_active_profile(user_id)
        if not rows_deleted:
            logger.warning(f"No active profile found to delete for user_id {user_id}")
            raise HTTPException(status_code=404, detail="No active profile found.")

        # Delete vectors from Qdrant
        delete_user_vectors(user_id)
        logger.info(f"Deleted profile and vectors for user_id {user_id}")

    except Exception as e:
        logger.error(f"Error deleting profile for user_id {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete profile.")

    return {"status": "deleted", "detail": "Profile and vectors deleted."}

"""
--------------------------------------------------------------------
Purpose:
    Allows users to delete (soft delete) their active profile. 
    Vectors in Qdrant are also deleted for security/cost.

What It Does:
    - Sets is_active=False in profiles table (Supabase)
    - Removes all user vectors from Qdrant
    - All actions logged and rate limited

Used By:
    - Dashboard 'Delete Profile' button

Good Practice:
    - Keeps inactive history in DB for possible future rollback
    - No file content or vectors remain after delete
    - Errors logged and user-facing

--------------------------------------------------------------------
"""
