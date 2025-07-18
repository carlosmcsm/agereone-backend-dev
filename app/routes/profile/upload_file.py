# app/routes/profile/upload_file.py ** NEW

import logging
from fastapi import APIRouter, UploadFile, HTTPException, Depends, Request, Form
from app.utils.text_extraction import extract_text_from_file
from app.services.vectorstore import delete_user_vectors, store_profile_vectors
from app.services.supabase import (
    deactivate_user_profiles,
    insert_user_profile_metadata,
    get_openai_key_and_model_for_user,
    get_user_profile_history,
)
from app.deps.supabase_auth import get_current_user
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload-file")
@limiter.limit(settings.RATE_LIMIT_UPLOAD_FILE)
async def upload_profile(
    request: Request,
    file: UploadFile,
    chunk_size: int = Form(None),  # for advanced users, else use default
    chunk_overlap: int = Form(None),  # for advanced users, else use default
    user=Depends(get_current_user),
):
    """
    Uploads and processes a new professional profile file for the user.
    - Only allows PDF, TXT, MD.
    - Old profiles (in Supabase) marked inactive, vectors deleted from Qdrant.
    - Only the latest upload is "active"; history is metadata only.
    - Requires OpenAI API key before embedding.
    - Supports default or custom chunking (if advanced option enabled).
    """
    logger.info(f"User '{user.get('email', '')}' ({user.get('user_id', '')}) uploading file: {file.filename}")

    # 1. Validate file type
    if not file.filename.endswith((".pdf", ".txt", ".md")):
        logger.warning(f"File {file.filename} rejected: unsupported type")
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, or Markdown (.md) files are allowed."
        )

    # 2. Read and extract text
    contents = await file.read()
    logger.info(f"Read {len(contents)} bytes from uploaded file {file.filename}")

    try:
        text = extract_text_from_file(contents, file.filename)
        logger.info(f"Extracted {len(text)} characters from file {file.filename}")
    except Exception as e:
        logger.error(f"Failed to extract text from {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text: {str(e)}"
        )

    if not text.strip():
        logger.warning(f"No text found in the uploaded file: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="No text found in the uploaded file."
        )

    user_id = user["user_id"]

    # 3. Check OpenAI key and model
    openai_key, embedding_model = get_openai_key_and_model_for_user(user_id)
    if not openai_key:
        logger.error(f"No OpenAI key configured for user_id {user_id}")
        raise HTTPException(
            status_code=400,
            detail="No OpenAI key configured. Please set your OpenAI API key before uploading a profile."
        )
    logger.info(f"OpenAI key and model found for user_id {user_id} ({embedding_model})")

    # 4. Handle chunk settings (default or user-provided)
    default_chunk_size = settings.DEFAULT_CHUNK_SIZE or 400
    default_chunk_overlap = settings.DEFAULT_CHUNK_OVERLAP or 20
    _chunk_size = chunk_size if chunk_size and chunk_size >= 100 else default_chunk_size
    _chunk_overlap = chunk_overlap if chunk_overlap and chunk_overlap >= 0 else default_chunk_overlap
    logger.info(f"Chunk settings: size={_chunk_size}, overlap={_chunk_overlap}")

    try:
        # 5. Mark all old profiles inactive in Supabase (history only)
        deactivate_user_profiles(user_id)
        logger.info(f"All previous profiles deactivated for user_id {user_id}")

        # 6. Delete all Qdrant vectors for this user
        delete_user_vectors(user_id)
        logger.info(f"All previous vectors deleted from Qdrant for user_id {user_id}")

        # 7. Chunk, embed, store vectors (Qdrant)
        vector_count = store_profile_vectors(
            user_id, text, openai_key=openai_key, model=embedding_model,
            chunk_size=_chunk_size, chunk_overlap=_chunk_overlap
        )
        logger.info(f"{vector_count} vectors embedded and stored for user_id {user_id}")

        # 8. Insert metadata row in Supabase
        insert_user_profile_metadata(
            user_id=user_id,
            file_name=file.filename,
            vector_count=vector_count,
            model=embedding_model,
            is_active=True,
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap
        )
        logger.info(f"New profile metadata inserted for user_id {user_id}")

    except Exception as e:
        logger.error(f"Embedding/upload error for user_id {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding error: {str(e)}"
        )

    return {"status": "uploaded", "active_file": file.filename, "vector_count": vector_count}

"""
--------------------------------------------------------------------
Purpose:
    Handle professional profile file uploads. Prepares text, chunks, embeds, and stores vector data for the user's AI career agent.

What It Does:
    - Accepts PDF/TXT/MD uploads from authenticated users.
    - Extracts text and validates file.
    - Requires user to have an OpenAI API key configured.
    - Marks all old profiles as inactive; deletes old vectors in Qdrant.
    - Embeds the new profile using chunking (default or user-specified, advanced).
    - Inserts new metadata row in Supabase with chunking info.
    - Only most recent upload is active (history is metadata only).

Used By:
    - Dashboard/profile upload page
    - Automated onboarding (file import)

Good Practice:
    - Never stores actual file, only metadata and active vectors (privacy, cost)
    - Enforces rate limiting, file validation, chunking config
    - Always logs key actions for debugging/audit

Business Logic:
    - Free users: default chunking only
    - Paid users: can customize chunking via dashboard
    - Only last upload is active; old files cannot be rolled back

Security & Scalability:
    - No file content stored in DB; Qdrant used for vectors only
    - OpenAI keys never logged; errors handled cleanly
    - Rate limits prevent abuse

--------------------------------------------------------------------
"""
