# app/utils/embedding.py ** New

import logging
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_text_embedding(text: str, openai_key: str = None, model: str = None):
    """
    Generates an embedding vector for the given text using OpenAI Embeddings API.
    """
    try:
        emb_model = model or settings.EMBEDDING_MODEL
        openai_api_key = openai_key or settings.OPENAI_API_KEY  # Use user’s key if provided!
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, model=emb_model)
        vector = embeddings.embed_query(text)
        return vector
    except Exception as e:
        logger.error(f"Error generating embedding for text: {e}", exc_info=True)
        return None

"""
--------------------------------------------------------------------
Purpose:
    Utility to get embedding vectors for any text string.
    Used by vectorstore.py and semantic search/chat.

What It Does:
    - Calls OpenAI Embeddings API for input text
    - Returns the vector for Qdrant/semantic search

Used By:
    - vectorstore.py (query_profile_vectors)
    - Any service that needs text→vector embedding

Good Practice:
    - Always uses user’s OpenAI key if provided (multi-tenant)
    - Handles exceptions/logs errors

--------------------------------------------------------------------
"""
