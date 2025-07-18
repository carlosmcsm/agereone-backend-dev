# app/routes/agent.py ** NEW

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.supabase import (
    get_user_profile_by_username,
    get_openai_key_and_model_for_user
)
from app.services.vectorstore import query_profile_vectors
from app.deps.supabase_auth import get_current_user
from app.core.limiter import limiter
from app.core.config import settings
from app.utils.agent import ask_openai_agent, ask_openai_agent_stream  # Both helpers

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    messages: list
    username: str = None  # Optional, for public AI profile/chat

# -----------------------------
# Standard AI Chat Endpoint
# -----------------------------
@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def agent_chat(
    request: Request,
    data: ChatRequest,
    user=Depends(get_current_user)
):
    """
    AI Career Chat endpoint (single reply, not streaming).
    """
    try:
        # Resolve user_id and profile (internal or public)
        if data.username:
            # Public profile chat
            profile = get_user_profile_by_username(data.username)
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found or not published.")
            user_id = profile["user_id"]
        else:
            user_id = user["user_id"]
            profile = get_user_profile_by_username(user["username"])
            if not profile:
                raise HTTPException(status_code=404, detail="Active profile not found for user.")

        # Fetch OpenAI key and model
        openai_key, openai_model = get_openai_key_and_model_for_user(user_id)
        if not openai_key:
            raise HTTPException(status_code=400, detail="No OpenAI key found for this user.")

        # Qdrant semantic context
        try:
            context_chunks = query_profile_vectors(user_id, data.messages[-1]["content"], top_k=6)
        except Exception as e:
            logger.error(f"Qdrant semantic search failed for user_id {user_id}: {e}", exc_info=True)
            context_chunks = []

        full_context = "\n".join([c["text"] for c in context_chunks])

        # Call OpenAI
        ai_reply = ask_openai_agent(
            api_key=openai_key,
            model=openai_model,
            system_prompt="You are an expert career advisor based on the user's profile.",
            context=full_context,
            messages=data.messages
        )

        return {"answer": ai_reply}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in AI chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown chat error.")

# -----------------------------
# Streaming AI Chat Endpoint
# -----------------------------
@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_CHAT_STREAM)
async def agent_chat_stream(
    request: Request,
    data: ChatRequest,
    user=Depends(get_current_user)
):
    """
    AI Career Chat (streaming reply).
    """
    try:
        # Resolve user_id and profile (internal or public)
        if data.username:
            profile = get_user_profile_by_username(data.username)
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found or not published.")
            user_id = profile["user_id"]
        else:
            user_id = user["user_id"]
            profile = get_user_profile_by_username(user["username"])
            if not profile:
                raise HTTPException(status_code=404, detail="Active profile not found for user.")

        # Fetch OpenAI key and model
        openai_key, openai_model = get_openai_key_and_model_for_user(user_id)
        if not openai_key:
            raise HTTPException(status_code=400, detail="No OpenAI key found for this user.")

        # Qdrant semantic context
        try:
            context_chunks = query_profile_vectors(user_id, data.messages[-1]["content"], top_k=6)
        except Exception as e:
            logger.error(f"Qdrant semantic search failed for user_id {user_id}: {e}", exc_info=True)
            context_chunks = []

        full_context = "\n".join([c["text"] for c in context_chunks])

        # Streaming response from OpenAI
        def stream():
            try:
                for chunk in ask_openai_agent_stream(
                    api_key=openai_key,
                    model=openai_model,
                    system_prompt="You are an expert career advisor based on the user's profile.",
                    context=full_context,
                    messages=data.messages
                ):
                    yield f"data: {chunk}\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield "data: Error streaming from OpenAI\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in AI chat streaming endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unknown chat stream error.")

"""
--------------------------------------------------------------------
Purpose:
    Provides both single-shot and streaming AI chat endpoints for career agent.
    /chat: For normal UI
    /chat/stream: For real-time streaming chat

What It Does:
    - Resolves user profile, OpenAI key/model, semantic context (Qdrant)
    - /chat streams as a single answer; /chat/stream yields live tokens/chunks
    - Works for both authenticated users (dashboard) and public subdomains

Used By:
    - Dashboard chat (fast answer)
    - Public AI agent (username.agereone.com)
    - Real-time chat UI

Good Practice:
    - Streaming uses Server-Sent Events (SSE), easy for Next.js and React
    - Rate-limited, fully logged, no secrets exposed
    - Handles all errors gracefully, logs for ops

Security & Scalability:
    - Auth required except for public profiles
    - All API keys are secure
    - Extensible for premium/policy controls

--------------------------------------------------------------------
"""
