# app/core/limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address

# ---------------------------------------------
# Rate Limiting Configuration
# ---------------------------------------------
# Limits each unique IP (get_remote_address) to 60 requests per minute by default.
limiter = Limiter(
    key_func=get_remote_address,     # Use the remote IP address as the identifier
    default_limits=["60/minute"]     # Change as needed per API best practices
)

"""
------------------------------------------------
✅ Purpose:
Protects your backend API from brute force, abuse, and accidental DDoS by rate-limiting clients per IP.

🔍 What It Does:
- Instantiates a `Limiter` from SlowAPI with a simple global rate limit.
- Used as middleware and exception handler in `main.py` to catch and handle too many requests.

📌 Used By:
- The FastAPI app (see main.py for app.state.limiter and SlowAPIMiddleware setup).
- Any endpoint can override or extend limits with SlowAPI decorators if needed.

🧠 Good Practices:
- Set a **reasonable default** for public APIs (e.g., 60/minute or less for free-tier).
- For more advanced plans, implement per-user limits using a key function based on JWT claims.
- Customize limits for sensitive endpoints (login, registration) to slow down abuse.
- Log or monitor rate-limit violations for ops visibility.

🔐 Security:
- Helps prevent basic denial-of-service and bot attacks.
- Not a substitute for true WAF/firewall, but excellent as first defense in SaaS.
- For production, consider using real user ID or API key for `key_func` if you want true per-user limits.

------------------------------------------------
"""
