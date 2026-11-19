# Technical Specification: Step 5.2a — Backend GitHub App Installation Webhook, Private Repo Token Exchange & Ingestion Router

## 1. Overview & Goal
RepoDefense requires access to private GitHub repositories when authorized by a candidate or organization. Rather than requesting broad, high-privilege personal access tokens (PATs), RepoDefense integrates with a dedicated GitHub App. This milestone establishes the backend infrastructure for the GitHub App:
1. Verifying HMAC SHA-256 signatures for GitHub App webhook events.
2. Generating short-lived RS256 JSON Web Tokens (JWTs) authenticated as the GitHub App.
3. Exchanging the App JWT for short-lived Installation Access Tokens scoped to candidate repositories.
4. Listing repositories accessible under an installation.
5. Providing authenticated endpoints for users to discover installation status, query accessible repositories, and initialize projects targeting private repositories using token-authenticated shallow cloning.
6. Ensuring strict zero-leakage security: credentials and access tokens are sanitized and never exposed in logs, API responses, or stored unencrypted.

## 2. Invariants & Guardrails
- **Tech Stack Compliance**: FastAPI (Python 3.12+), Pydantic v2, PostgreSQL 17, `cryptography` / `PyJWT` for RS256 token generation, `httpx` for async GitHub API integration.
- **Strict LOC Limit**: All Python files strictly $\le 300$ lines of code.
- **Security & Zero Arbitrary Code Execution**: Untrusted repository content is analyzed purely statically. Credentials (`x-access-token`) are strictly redacted from URLs before logging or recording.
- **Webhook Security**: All incoming webhook events to `/api/v1/github-app/webhook` are cryptographically verified using HMAC SHA-256 with constant-time comparison (`hmac.compare_digest`).
- **Tenant Isolation & IDOR Protection**: Endpoints querying installation repositories or creating projects verify that the caller is authenticated via Supabase JWT.

## 3. Architecture & Data Contracts

### 3.1 Configuration Settings (`backend/app/core/config.py`)
Add GitHub App settings with safe default fallbacks:
- `GITHUB_APP_ID`: str = ""
- `GITHUB_APP_PRIVATE_KEY`: str = "" (PEM format RS256 private key or base64)
- `GITHUB_APP_WEBHOOK_SECRET`: str = "" (Webhook signature secret)
- `GITHUB_APP_CLIENT_ID`: str = ""
- `GITHUB_APP_CLIENT_SECRET`: str = ""
- `GITHUB_APP_SLUG`: str = "repodefense-app"

### 3.2 Pydantic Schemas (`backend/app/schemas/github_app.py`)
- `GitHubAppStatusResponse`:
  - `configured: bool`
  - `app_id: str | None`
  - `app_slug: str | None`
  - `install_url: str | None`
- `GitHubAppRepoItem`:
  - `id: int`
  - `name: str`
  - `full_name: str`
  - `private: bool`
  - `default_branch: str`
  - `description: str | None`
  - `clone_url: str`
  - `html_url: str`
- `GitHubAppRepoListResponse`:
  - `installation_id: int`
  - `total_count: int`
  - `repositories: list[GitHubAppRepoItem]`
- `PrivateRepoProjectCreate`:
  - `full_name: str` (e.g. `owner/repo`)
  - `installation_id: int`
  - `default_branch: str = "main"`
- `GitHubWebhookResponse`:
  - `status: str`
  - `event: str`
  - `action: str | None`

### 3.3 GitHub App Service (`backend/app/services/github_app.py`)
- `verify_webhook_signature(payload_bytes: bytes, signature_header: str | None) -> bool`
- `generate_app_jwt(app_id: str, private_key_pem: str, expiration_seconds: int = 600) -> str`
- `get_installation_access_token(installation_id: int) -> str`
- `list_installation_repositories(installation_id: int) -> list[dict]`
- `build_authenticated_clone_url(clone_url: str, token: str) -> str`
- `redact_token_from_url(url: str) -> str`

### 3.4 API Router (`backend/app/api/v1/github_app.py`)
- `GET /api/v1/github-app/status`: Returns status & installation URL.
- `POST /api/v1/github-app/webhook`: Verifies HMAC signature and processes `installation` and `installation_repositories` events.
- `GET /api/v1/github-app/installations/{installation_id}/repositories`: Authenticated endpoint returning accessible repositories for the installation.
- `POST /api/v1/github-app/projects`: Authenticated endpoint that provisions a Project from an accessible private repository, configures the clone URL with token authentication, and enqueues the cloner job.

## 4. Verification Plan
- Unit & integration tests in `backend/tests/test_github_app.py`:
  1. Signature verification (valid vs invalid HMAC).
  2. JWT generation & RS256 validation.
  3. Installation token exchange mock.
  4. Repository listing and pagination handling.
  5. Private project creation & clone URL credential redaction.
  6. Endpoint authentication & error handling.
- Lint & format check: `python -m ruff check backend/`.
- Test execution: `pytest backend/tests/test_github_app.py -v`.
