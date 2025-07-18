# app/routes/health.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """
    Simple health check endpoint.

    Returns:
        JSON with status "ok" for uptime monitoring and readiness probes.
    """
    return {"status": "ok"}

"""
------------------------------------------------------------
✅ Purpose:
Provides a lightweight endpoint to verify the API is up and responsive.

🔍 What It Does:
- Returns {"status": "ok"} with a 200 status code if FastAPI is running.
- Used by orchestration tools (Kubernetes, Railway, Vercel), load balancers, and monitoring systems.

📌 Used By:
- Cloud deployment platforms (readiness/liveness probe)
- Uptime monitors
- CI/CD health checks

🧠 Good Practices:
- Keep this endpoint fast and side-effect free (no DB or external calls).
- Never require authentication for `/health`.
- Should always return 200 (unless the server is truly down).

🔐 Security:
- Does NOT leak sensitive information.
- Safe to expose publicly.

------------------------------------------------------------
"""
