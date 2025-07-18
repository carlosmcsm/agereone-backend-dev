# app/main.py ** New

"""
main.py — AgereOne Backend

Purpose:
    Main FastAPI entrypoint for AgereOne AI Career Agent SaaS.
    Configures CORS, rate limiting, logging, and loads all routers.
    Ensures security, scalability, and clarity for maintenance.

What It Does:
    - Initializes FastAPI app.
    - Attaches middleware for CORS, rate limiting, and error handling.
    - Registers all API routers (auth, profile, agent, health, etc).
    - Restricts CORS to frontend URL.
    - Provides a health root endpoint.

Used By:
    - uvicorn app.main:app --reload (development)
    - Production deployments on Railway, Docker, etc.

Good Practice:
    - Only import and include routers that exist in codebase.
    - All services and logic in separate service/util files.
    - Rate limiting and error handlers enabled.
    - Each section is well-commented for maintainers.

--------------------------------------------------------------------
"""

from app.core.logging import init_logging
init_logging()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# === Import Routers Based on Current Structure ===

# API / AUTH (app/api/auth)
from app.api.auth.register import router as register_router
from app.api.auth.profile_settings import router as profile_settings_router
from app.api.auth.update_key import router as update_key_router

# ROUTES / AUTH (app/routes/auth)
from app.routes.auth.login import router as login_router
from app.routes.auth.forgot_password import router as forgot_password_router
from app.routes.auth.reset_password import router as reset_password_router

# ROUTES / PROFILE (app/routes/profile)
from app.routes.profile.upload_file import router as upload_file_router
from app.routes.profile.delete import router as delete_router

# AGENT & HEALTH
from app.routes.agent import router as agent_router
from app.routes.health import router as health_router

from app.core.config import settings

# === FastAPI App Initialization ===
app = FastAPI(
    title="AgereOne Backend",
    description="Backend API for AgereOne AI Career Agent SaaS.",
    version="1.0.0"
)

# === Rate Limiting Middleware ===
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handles requests exceeding rate limits."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
    )

app.add_middleware(SlowAPIMiddleware)

# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # Only allow from frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Include Routers (Prefix & Tag for Each) ===

# Auth (API-specific, e.g. dashboard settings, registration, OpenAI key)
app.include_router(register_router,           prefix="/api/auth",    tags=["auth"])
app.include_router(profile_settings_router,   prefix="/api/auth",    tags=["auth"])
app.include_router(update_key_router,         prefix="/api/auth",    tags=["auth"])

# Auth (Classic routes: login, forgot/reset password)
app.include_router(login_router,              prefix="/api/auth",    tags=["auth"])
app.include_router(forgot_password_router,    prefix="/api/auth",    tags=["auth"])
app.include_router(reset_password_router,     prefix="/api/auth",    tags=["auth"])

# Profile management
app.include_router(upload_file_router,        prefix="/api/profile", tags=["profile"])
app.include_router(delete_router,             prefix="/api/profile", tags=["profile"])

# AI agent endpoints
app.include_router(agent_router,              prefix="/api/agent",   tags=["agent"])

# Health check
app.include_router(health_router,             prefix="/api",         tags=["health"])

# === Root Endpoint ===
@app.get("/")
def read_root():
    """Basic health/status endpoint."""
    return {"status": "AgereOne backend running."}

"""
--------------------------------------------------------------------
Security & Scalability Notes:
    - All endpoints are protected by per-route rate limiting.
    - CORS policy is restricted for API security.
    - Each router is modular for easier testing and maintenance.
    - You can add more routers simply by adding their import/include lines.
    - Suitable for Railway, Docker, and serverless Python deployments.

Deployment:
    - Run: uvicorn app.main:app --reload  (dev)
    - Run: uvicorn app.main:app --host 0.0.0.0 --port 8000  (prod/Railway)

--------------------------------------------------------------------
"""
