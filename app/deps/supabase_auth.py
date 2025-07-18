# app/deps/supabase_auth.py

from fastapi import Header, HTTPException
from jose import jwt
import requests
from functools import lru_cache
from app.core.config import settings
import os

# --- Supabase Auth JWT validation setup ---

# Use the new JWKS endpoint (as of Supabase 2024+) for ECC (ES256) JWTs.
JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# ANON API Key, used for requests to JWKS endpoint. Load from env or config.
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or settings.SUPABASE_ANON_KEY

@lru_cache()
def get_supabase_jwks():
    """
    Downloads and caches the JWKS used to validate Supabase JWT tokens.
    Sends 'apikey' header as required by Supabase for all non-public endpoints.
    Caching avoids unnecessary network requests for every validation.
    """
    headers = {"apikey": SUPABASE_ANON_KEY} if SUPABASE_ANON_KEY else {}
    resp = requests.get(JWKS_URL, headers=headers)
    resp.raise_for_status()  # Raise HTTP 4xx/5xx as exceptions
    return resp.json()       # JWKS format

def decode_supabase_token(token: str):
    """
    Decodes and verifies a JWT token issued by Supabase using the project's JWKS.
    - Uses the cached JWKS public keys.
    - Disables audience ('aud') check for compatibility (adjust if needed).
    - Uses ES256 algorithm for ECC keys (modern Supabase).
    """
    jwks = get_supabase_jwks()
    try:
        return jwt.decode(
            token,
            jwks,
            algorithms=["ES256"],  # Supabase now uses ECC (P-256)
            options={"verify_aud": False}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Supabase token: {str(e)}")

async def get_current_user(authorization: str = Header(...)):
    """
    FastAPI dependency for extracting and validating the logged-in user from Authorization header.
    - Expects: 'Authorization: Bearer <token>'
    - Decodes the JWT and returns a dict with user_id, email, and role.
    - Raises HTTP 401 for missing or invalid tokens.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.split(" ")[1]
    payload = decode_supabase_token(token)

    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
    }

"""
----------------------------------------------------------
📝 Implementation Notes & Troubleshooting

1. JWKS endpoint:
   - Use '/auth/v1/.well-known/jwks.json' for all modern Supabase projects.
   - The old '/auth/v1/keys' endpoint no longer exists on new projects (returns 404).

2. JWT Algorithm:
   - Supabase migrated to ES256 (ECC, P-256) by default. Use 'algorithms=["ES256"]'.
   - Do NOT use RS256 unless your project explicitly uses RSA keys.

3. JWKS API key:
   - Supabase requires the 'apikey' header on almost all endpoints, including JWKS.
   - Always send your ANON key in the header for backend-to-backend calls.

4. JWT claims:
   - The 'sub' field is the user ID (UUID).
   - The 'email' claim is only present if email is verified/available.
   - The 'role' claim reflects the user's auth role (usually 'authenticated').

5. Caching:
   - @lru_cache caches the public key set for the process lifetime (improves perf).
   - If you rotate keys, restart your backend or clear the cache.

6. Security:
   - Always verify tokens using your project's real JWKS.
   - Never trust tokens unless verified.
   - Use HTTPS for all API and frontend/backend communication.

7. Troubleshooting:
   - 404 from '/auth/v1/keys'? You're on a new project—switch to '.well-known/jwks.json'.
   - 401/Invalid Signature? Check algorithm (ES256 vs RS256) and key rotation status.
   - If you can't fetch the JWKS, check your Supabase URL and API key validity.
----------------------------------------------------------
"""


"""
------------------------------------------------
✅ Purpose:
Reusable FastAPI dependency for validating and extracting user identity from Supabase Auth JWTs.

🔍 What It Does:
- Fetches/caches the Supabase JWKS (public keys for verifying JWT).
- Decodes/validates Authorization Bearer JWT.
- Makes the current user available to protected endpoints.

📌 Used by:
- All routes requiring authentication, via: `Depends(get_current_user)`

🧠 Good Practices:
- Use @lru_cache for caching the JWKS (saves requests, boosts perf).
- Always check the structure and claims of decoded payload.
- For stricter security, verify the audience claim (if you set one).

🔐 Security:
- Only ever trust validated JWTs; do not skip decode/verify.
- Never expose raw token data to the client.
- Use HTTPS everywhere (prevents token sniffing).
------------------------------------------------
"""
