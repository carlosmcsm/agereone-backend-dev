# app/core/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache

# ---------------------------------------------
# Settings class for all configuration values
# ---------------------------------------------
class Settings(BaseSettings):
    # Qdrant settings
    QDRANT_URL: str
    QDRANT_API_KEY: str
    
    # Default model
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Supabase settings
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Frontend URL (used for CORS)
    FRONTEND_URL: str = "http://localhost:3000"

    RATE_LIMIT_FORGOT_PASSWORD: str = "5/hour"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_RESET_PASSWORD: str = "5/hour"
    RATE_LIMIT_DELETE_PROFILE: str = "5/minute"
    RATE_LIMIT_UPLOAD_FILE: str = "10/minute"
    RATE_LIMIT_UPLOAD_STRUCTURED: str = "5/minute"
    RATE_LIMIT_UPDATE_KEY: str = "10/minute"
    RATE_LIMIT_CHAT: str = "10/minute"
    RATE_LIMIT_CHAT_STREAM: str = "20/minute"

    DEFAULT_CHUNK_SIZE: int = 400
    DEFAULT_CHUNK_OVERLAP: int = 20

    class Config:
        env_file = ".env"  # Load variables from .env by default

# ---------------------------------------------
# Singleton pattern for config (caches instance)
# ---------------------------------------------
@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()  # This is what you import elsewhere

"""
------------------------------------------------
✅ Purpose:
Centralizes all environment-based configuration for the SaaS backend.
This file makes it easy to switch between dev/prod and keeps secrets out of code.

🔍 What It Does:
- Loads and type-checks all sensitive config from environment or .env file.
- Exposes a singleton `settings` object for safe, easy access throughout your app.
- Caches config for performance (using @lru_cache).

📌 Used By:
- Any backend module that needs credentials, URLs, or other env-specific config.
- Typically imported as `from app.core.config import settings`.

🧠 Good Practices:
- NEVER hardcode credentials—always use env vars.
- Always use `lru_cache` so config is loaded only once.
- Add new fields to the Settings class as your platform grows.
- Consider adding an ENV field for conditional logic (e.g., logging).

🔐 Security:
- Do not commit your `.env` files or secrets to version control.
- For production, set variables using real environment variables, not just `.env`.
- Rotate keys when needed—restart the backend to reload.
- If you add secrets, use Pydantic validators to enforce strict formats (e.g., URLs).

------------------------------------------------
"""
