# app/services/cloudflare.py ** NEW

import logging
import os
import httpx

logger = logging.getLogger(__name__)

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")

async def create_subdomain_record(username: str, root_domain: str = "agereone.com"):
    """
    Asynchronously creates a CNAME DNS record in Cloudflare for a user's subdomain.
    """
    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ZONE_ID:
        logger.error("Cloudflare credentials (token/zone id) are not set.")
        raise Exception("Cloudflare credentials (token/zone id) not set in environment variables.")

    # Basic sanity check
    if not username.isalnum():
        logger.error(f"Invalid username for subdomain: '{username}'")
        raise Exception("Username for subdomain must be alphanumeric.")

    api_url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    record_data = {
        "type": "CNAME",
        "name": f"{username}.{root_domain}",
        "content": root_domain,
        "ttl": 3600,
        "proxied": True
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            logger.info(f"Creating subdomain: {record_data['name']} (CNAME -> {root_domain})")
            response = await client.post(api_url, headers=headers, json=record_data)

        if response.status_code not in (200, 201):
            logger.error(f"Cloudflare API error: {response.status_code} - {response.text}")
            raise Exception(f"Cloudflare API error: {response.status_code} - {response.text}")

        logger.info(f"Cloudflare subdomain created: {record_data['name']}")
        return response.json()

    except Exception as e:
        logger.error(f"Failed to create Cloudflare DNS record for {username}: {e}", exc_info=True)
        raise

"""
--------------------------------------------------------------
Purpose:
    Automates creation of per-user subdomains (e.g., johndoe.agereone.com) in Cloudflare DNS.

What It Does:
    - Authenticates with Cloudflare using API token.
    - Creates a proxied CNAME DNS record for the given username.
    - Intended for SaaS platforms offering user subdomains.

Used By:
    - Account creation/onboarding logic, e.g., in your `/register` or admin user creation flows.

Good Practices:
    - Use short TTLs for test/staging; longer for production.
    - Catch and log exceptions—subdomain creation should not bring down your main app.
    - Rate limit Cloudflare API calls if looping/automating.
    - Validate all user input (no wildcards, scriptable names, etc).

Security & Scalability:
    - Do NOT hardcode tokens; use env vars or secret managers.
    - Always use HTTPS for API requests.
    - NEVER expose Cloudflare API keys to frontend or end users.

--------------------------------------------------------------
"""
