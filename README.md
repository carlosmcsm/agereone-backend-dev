# API Route Table

| Route Prefix   | HTTP Method | Path / Suffix                  | File Location                             | Description                      |
| -------------- | ----------- | ------------------------------ | ----------------------------------------- | -------------------------------- |
| `/api/auth`    | POST        | `/register`                    | `app/api/auth/register.py`                | Register a new user              |
| `/api/auth`    | POST        | `/update-key`                  | `app/api/auth/update_key.py`              | Update OpenAI API key and model  |
| `/api/auth`    | GET         | `/get-user-metadata`           | `app/api/auth/get_user_metadata.py`       | Get metadata for logged-in user  |
| `/api/auth`    | POST        | `/login`                       | `app/routes/auth/login.py`                | Login with email and password    |
| `/api/auth`    | POST        | `/forgot-password`             | `app/routes/auth/forgot_password.py`      | Trigger forgot password email    |
| `/api/auth`    | POST        | `/reset-password`              | `app/routes/auth/reset_password.py`       | Reset password via token         |
| `/api/auth`    | GET         | `/profile-settings/{username}` | `app/routes/auth/profile_settings.py`     | Get OpenAI key/model for user    |
| `/api/profile` | POST        | `/upload`                      | `app/api/profile/upload.py`               | Upload profile (JSON)            |
| `/api/profile` | POST        | `/upload-file`                 | `app/routes/profile/upload_file.py`       | Upload profile file (PDF/TXT/MD) |
| `/api/profile` | POST        | `/upload-structured`           | `app/routes/profile/upload_structured.py` | Upload profile (structured JSON) |
| `/api/profile` | DELETE      | `/delete`                      | `app/routes/profile/delete.py`            | Delete user profile              |
| `/api/agent`   | POST        | `/chat`                        | `app/routes/agent.py`                     | AI agent chat endpoint           |
| `/api/agent`   | POST        | `/chat/stream`                 | `app/routes/agent.py`                     | Streamed agent chat              |
| `/api`         | GET         | `/health`                      | `app/routes/health.py`                    | Healthcheck endpoint             |


# Notes
- Prefix is always combined with the HTTP method and the path suffix for the full route.
- All /api/auth endpoints are for authentication/user management.
- All /api/profile endpoints are for profile upload, deletion, and management.
- All /api/agent endpoints are for AI chat services.
- /api/health is a simple healthcheck endpoint.

# Start
% uv venv
% uv pip install -r requirements.txt -- If needed
% source .venv/bin/activate
% uvicorn app.main:app --reload


# 🚀 AgereOne SaaS – Endpoint Workflows and Functional Description (2025, Updated)
1. User Registration (/api/auth/register)
- Fields: email, password, first name, last name, username.
- Validations:
    Email: unique, valid format
    Password: strong (≥8 chars, uppercase/lowercase/digit/special)
    Username: unique, ≥8 chars, must contain at least one digit
- Initial Plan: Always registered as free
- Domain assignment:
    free → <hash>.agereone.com
    User can upgrade plan in dashboard to get username.agereone.com
- Supabase: Handles Auth, confirmation email sent

2. User Login (/api/auth/login)
- Flow: Email/password → JWT issued
- Validations: Email must be verified

3. Upload Career Profile (/api/profile/upload-file)
- Requires Auth: Yes
- File Types: PDF, TXT, MD
- Chunking:
    Default: System uses standard chunk size (e.g., 400 chars, 20 overlap).
    Advanced: Allow users (optionally, in dashboard) to set custom chunk size/overlap.
        Note: Changing chunk settings requires re-uploading the profile file, and system warns users that embeddings will be regenerated.
- Flow:
    1. Validate file type/size
    2. Extract text from file
    3. If user has no OpenAI key, return error ("Please set your OpenAI key")
    4. Mark all previous profiles as inactive for this user
    5. Remove all vectors from Qdrant for this user
    6. Insert new row in profiles (filename, vector_count=0, model, is_active=True, chunk config used)
    7. Chunk text (with user’s config or default)
    8. Generate embeddings (one per chunk)
    9. Store vectors in Qdrant, update vector count in profiles row
- History/Uploads:
    The dashboard lists metadata of all past uploads (filename, date, model, vector count), but does not store the file itself or allow rollback. Only the latest upload is active; past uploads are reference-only.
- Dashboard:
    Show uploads history for audit.
    Clarify: Only the last uploaded file is active. Past uploads are for records; to re-activate, re-upload the file.

4. Save/Update OpenAI API Key (/api/auth/update-key)
- Requires Auth: Yes
- Flow:
    1. User enters/pastes OpenAI API key and selects model from dropdown
    2. Backend validates and stores in openai_keys (1 row per user)
    3. Model dropdown shows only supported/compliant models

5. Fetch User Profile Settings (/api/auth/profile-settings)
- Requires Auth: Yes
- Returns:
    List of uploaded files (filename, date, is_active)
    OpenAI key (masked) and model
    Subdomain (and status: free/paid)
    Plan, queries remaining (if free)
- Rollback:
    Not possible unless file is re-uploaded. Dashboard clearly explains that only the last upload is active.
- System Prompt:
    User can update their AI system prompt, saved in profile or settings.

6. AI Chat Endpoint (/api/agent/chat)
- Types:
    Dashboard: Authenticated user, full access (within limits)
    Public subdomain: No auth, if is_published=True
- Flow:
    1. Identify user (from JWT or subdomain)
    2. Retrieve vectors for active profile
    3. Query OpenAI with user key/model and context, using the user’s system prompt
    4. Rate limit: 
        Free: X queries/day, Y seconds between requests
        Paid: higher/faster limits

7. AI Chat Streaming Endpoint (/api/agent/chat/stream)
- Same as above, but streams OpenAI reply

8. Delete Profile (/api/profile/delete)
- Requires Auth: Yes
- Flow:
    1. Mark all profiles for user as is_active=False
    2. Remove vectors from Qdrant
    3. Log this for analytics

9. Forgot Password (/api/auth/forgot-password)
- Only for users not logged in.
- Triggers Supabase reset email.

10. Reset Password (/api/auth/reset-password)
- User completes reset using token from email.

11. Public Subdomain/AI Profile Page
- Free: <hash>.agereone.com (unique per user, not vanity)
- Paid: username.agereone.com
- Upgrade/downgrade:
    On upgrade, update DNS/Cloudflare and mark new subdomain as active
    On downgrade, revert to hash subdomain
- Only visible if is_published=True
- SEO: Metadata set dynamically per user/profile

12. Plan Management, Stripe, Analytics
- Endpoints:
    /api/plan/subscribe — Starts a Stripe subscription session
    /api/plan/webhook — Stripe webhook for payments, renewals, cancel, upgrade/downgrade
    /api/plan/status — User’s current plan, expiry, invoice links
    /api/analytics/usage — Return API/chat usage, queries, remaining quota

Gating: All backend endpoints check plan before allowing access to premium features

AgereOne SaaS – Feature & Endpoint Summary Table
| Endpoint / Feature           | DB Tables Used                 | Free Plan                                       | Paid Plan                                                                 | Notes                                            |
| ---------------------------- | ------------------------------ | ----------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------ |
| **Register**                 | users                          | `<hash>.agereone.com` subdomain                 | Can upgrade to `username.agereone.com`                                    | All users start free, upgrade in dashboard       |
| **Login**                    | users                          | Yes                                             | Yes                                                                       | Only after email verification                    |
| **Upload Profile**           | profiles, qdrant               | 1 active; history (metadata only)               | 1 active; history (metadata only)                                         | Only most recent upload is active, no rollback   |
| **Chunk Settings**           | profiles                       | Default (not configurable)                      | User-configurable (advanced option)                                       | Must re-upload file to change chunking           |
| **OpenAI Key/Model**         | openai\_keys                   | User sets key, limited model choice             | User sets key, all supported models                                       | Model options shown in dropdown                  |
| **View Uploads History**     | profiles                       | Yes (filenames, upload dates, active)           | Yes (filenames, upload dates, active)                                     | Old files not stored, only metadata              |
| **Activate/Publish Profile** | profiles                       | Yes, but only one active at a time              | Yes, but only one active at a time                                        | "Published" flag controls public visibility      |
| **AI Chat (Dashboard)**      | profiles, qdrant, openai\_keys | Limited queries (rate-limited)                  | More queries, faster rate, priority                                       | Rate limits per plan, can test own profile       |
| **AI Chat (Public)**         | profiles, qdrant               | Only if `is_published=True`, free subdomain     | Only if `is_published=True`, vanity subdomain                             | Public chat page, domain depends on plan         |
| **Delete Profile**           | profiles, qdrant               | Yes                                             | Yes                                                                       | Soft-delete in DB, hard delete vectors in Qdrant |
| **Forgot/Reset Password**    | users (Supabase)               | Yes                                             | Yes                                                                       | Handled via Supabase                             |
| **System Prompt Setting**    | profiles/settings              | Default only                                    | User-configurable                                                         | Paid users can edit system prompt                |
| **Custom Chunk Size**        | profiles                       | No                                              | Yes (Advanced Settings)                                                   | Must re-upload file if changed                   |
| **Subdomain**                | users                          | `<hash>.agereone.com`                           | `username.agereone.com`                                                   | Upgrades update DNS and mapping                  |
| **Stripe/Billing**           | users, Stripe                  | Upgrade option only                             | Monthly/Yearly (auto-renew)                                               | Billing handled with Stripe                      |
| **Analytics/Usage**          | profiles, usage logs           | Basic                                           | Full (usage stats, invoices, quota)                                       | Per user                                         |
| **Dashboard Controls**       | profiles, openai\_keys         | Basic (key, file, queries left, publish toggle) | Advanced (all free features + system prompt, chunk size, usage analytics) |                                                  |

# Legend:
- Active = currently used for AI chat (only latest upload’s vectors are stored/used).
- History = past file uploads metadata (not recoverable).
- Published = profile visible at public subdomain.
