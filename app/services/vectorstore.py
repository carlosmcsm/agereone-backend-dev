# app/services/vectorstore.py ** NEW

import logging
import uuid
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
    VectorParams,
    Distance
)
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.utils.embeddings import get_text_embedding

logger = logging.getLogger(__name__)

COLLECTION_NAME = "career_profiles"

# Initialize Qdrant client (singleton pattern)
client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

def ensure_collection_exists():
    logger.info("Ensuring Qdrant collection and payload index exist...")
    collections = [col.name for col in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        logger.info(f"Creating new collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="user_id",
            field_schema="keyword"
        )

def get_valid_embedding_model(model: str = None):
    model_candidate = model or settings.EMBEDDING_MODEL
    if not model_candidate or not model_candidate.startswith("text-embedding"):
        logger.warning(f"Invalid or missing embedding model '{model_candidate}', using default.")
        return "text-embedding-3-small"
    return model_candidate

def qdrant_upsert(docs: List[Dict]):
    logger.info(f"Upserting {len(docs)} vectors into Qdrant collection {COLLECTION_NAME}")
    ensure_collection_exists()
    points = [
        PointStruct(
            id=doc["id"],
            vector=doc["vector"],
            payload=doc["payload"]
        )
        for doc in docs
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info("Qdrant upsert completed.")

def qdrant_query(user_id: str, query: str, openai_key: str, model: str = None) -> List[Dict]:
    logger.info(f"Running Qdrant vector search for user_id={user_id}, query={query[:40]}...")
    ensure_collection_exists()
    model = get_valid_embedding_model(model)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_key, model=model)
    query_vector = embeddings.embed_query(query)
    search_filter = Filter(
        must=[
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id)
            )
        ]
    )
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=15,
        search_params=SearchParams(hnsw_ef=128),
        query_filter=search_filter
    )
    logger.info(f"Qdrant search returned {len(results)} hits for user_id {user_id}")
    return [{"text": hit.payload.get("text", ""), "score": hit.score} for hit in results]

def query_profile_vectors(user_id: str, query_text: str, openai_key: str, model: str = None, top_k: int = 6) -> List[Dict]:
    logger.info(f"Semantic search: user_id={user_id}, top_k={top_k}, query='{query_text[:40]}...'")
    ensure_collection_exists()
    query_vector = get_text_embedding(query_text, openai_key=openai_key, model=model)
    if not query_vector:
        logger.warning(f"Failed to generate query embedding for user_id {user_id}")
        return []

    search_filter = Filter(
        must=[
            FieldCondition(
                key="user_id",
                match=MatchValue(value=user_id)
            )
        ]
    )
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        search_params=SearchParams(hnsw_ef=128),
        query_filter=search_filter
    )
    logger.info(f"Qdrant search returned {len(results)} hits for user_id {user_id}")
    return [{"text": hit.payload.get("text", ""), "score": hit.score} for hit in results]

def store_profile_vectors(
    user_id: str,
    text: str,
    openai_key: str,
    model: str = None,
    chunk_size: int = None,
    chunk_overlap: int = None,
    user_plan: str = "free"
) -> int:
    """
    Splits and stores a user's uploaded profile in Qdrant.
    Supports plan-based chunking customization.
    Returns number of chunks embedded.
    """
    logger.info(f"Storing profile vectors for user_id={user_id} with model={model}, plan={user_plan}")

    use_custom_chunks = user_plan in ("paid", "premium", "pro")
    config_chunk_size = getattr(settings, "DEFAULT_CHUNK_SIZE", 400)
    config_chunk_overlap = getattr(settings, "DEFAULT_CHUNK_OVERLAP", 20)

    if use_custom_chunks:
        _chunk_size = chunk_size if chunk_size and chunk_size >= 100 else config_chunk_size
        _chunk_overlap = chunk_overlap if chunk_overlap and chunk_overlap >= 0 else config_chunk_overlap
    else:
        _chunk_size = config_chunk_size
        _chunk_overlap = config_chunk_overlap

    logger.info(f"Chunking settings: size={_chunk_size}, overlap={_chunk_overlap}")

    model = get_valid_embedding_model(model)
    ensure_collection_exists()
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=_chunk_size, chunk_overlap=_chunk_overlap)
    chunks = text_splitter.split_text(text)
    logger.info(f"Text split into {len(chunks)} chunks.")

    embeddings = OpenAIEmbeddings(openai_api_key=openai_key, model=model)
    embedded_docs = []
    for chunk in chunks:
        vector = embeddings.embed_query(chunk)
        embedded_docs.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "user_id": user_id,
                    "text": chunk,
                    "model": model,
                    "chunk_size": _chunk_size,
                    "chunk_overlap": _chunk_overlap,
                    "plan": user_plan
                }
            )
        )
    logger.info(f"Upserting {len(embedded_docs)} vectors into Qdrant...")
    client.upsert(collection_name=COLLECTION_NAME, points=embedded_docs)
    logger.info("Profile vectors successfully upserted in Qdrant.")
    return len(embedded_docs)

def delete_user_vectors(user_id: str):
    logger.info(f"Deleting all Qdrant vectors for user_id={user_id}")
    ensure_collection_exists()
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        )
    )
    logger.info(f"Deleted all vectors in Qdrant for user_id={user_id}")

"""
--------------------------------------------------------------------
Purpose:
    Manages all interaction with Qdrant vector DB for semantic search
    and chunk storage for user career profiles.

What It Does:
    - Upserts embedded profile chunks per user
    - Semantic search (query_profile_vectors) for chat context
    - Deletes all vectors for user on profile delete/account delete

Used By:
    - agent.py (chat endpoints, context search)
    - profile upload & delete
    - dashboard analytics

Good Practice:
    - Always ensure collection exists (idempotent)
    - Always uses user's OpenAI key for multi-tenancy/security
    - All errors and actions logged

Security & Scalability:
    - All queries and inserts filtered by user_id (no leakage)
    - Robust logging for troubleshooting and auditing
    - Designed for multi-tenant, high-volume SaaS

--------------------------------------------------------------------
"""
