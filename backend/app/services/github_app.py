"""GitHub App integration service for private repository authentication."""

import base64
import hashlib
import hmac
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import jwt
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_CREDENTIALS_RE = re.compile(r"https?://([^/@:]+(:[^/@:]+)?@)")


def verify_webhook_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None,
) -> bool:
    """Verifies HMAC SHA-256 signature from GitHub webhook headers."""
    expected_secret = secret or settings.GITHUB_APP_WEBHOOK_SECRET
    if not expected_secret or not signature_header:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    received_sig = signature_header[len(prefix) :].strip()
    computed_sig = hmac.new(
        key=expected_secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_sig.lower(), received_sig.lower())


def _normalize_private_key(key_input: str) -> str:
    """Normalizes raw or base64-encoded PEM private key."""
    cleaned = key_input.strip()
    if "-----BEGIN" in cleaned:
        return cleaned
    try:
        decoded = base64.b64decode(cleaned).decode("utf-8")
        if "-----BEGIN" in decoded:
            return decoded
    except Exception:
        pass
    return cleaned


def generate_app_jwt(
    app_id: Optional[str] = None,
    private_key: Optional[str] = None,
    expiration_seconds: int = 600,
) -> str:
    """Generates an RS256 JWT authenticated as the GitHub App."""
    effective_app_id = app_id or settings.GITHUB_APP_ID
    effective_key = private_key or settings.GITHUB_APP_PRIVATE_KEY

    if not effective_app_id or not effective_key:
        raise ValueError("GitHub App ID and private key must be configured")

    pem_key = _normalize_private_key(effective_key)
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + min(expiration_seconds, 600),
        "iss": effective_app_id,
    }

    return jwt.encode(payload, pem_key, algorithm="RS256")


async def get_installation_access_token(
    installation_id: int,
    app_jwt: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> str:
    """Exchanges GitHub App JWT for a scoped installation access token."""
    token_jwt = app_jwt or generate_app_jwt()
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {token_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async def _post(c: httpx.AsyncClient) -> str:
        resp = await c.post(url, headers=headers, timeout=15.0)
        if resp.status_code != 201:
            logger.error("github_token_exchange_failed", status=resp.status_code, text=resp.text)
            raise RuntimeError(f"GitHub token exchange failed with status {resp.status_code}")
        data = resp.json()
        return data["token"]

    if client:
        return await _post(client)
    async with httpx.AsyncClient() as c:
        return await _post(c)


async def list_installation_repositories(
    installation_id: int,
    client: Optional[httpx.AsyncClient] = None,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Retrieves all repositories accessible by the given installation."""
    token = await get_installation_access_token(installation_id, client=client)
    url = "https://api.github.com/installation/repositories"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async def _get(c: httpx.AsyncClient) -> Tuple[int, List[Dict[str, Any]]]:
        resp = await c.get(url, headers=headers, timeout=20.0)
        if resp.status_code != 200:
            logger.error("github_list_repos_failed", status=resp.status_code, text=resp.text)
            raise RuntimeError(f"Failed to fetch repositories: {resp.status_code}")
        data = resp.json()
        total = data.get("total_count", 0)
        repos = data.get("repositories", [])
        return total, repos

    if client:
        return await _get(client)
    async with httpx.AsyncClient() as c:
        return await _get(c)


def build_authenticated_clone_url(clone_url: str, token: str) -> str:
    """Injects short-lived installation access token into clone URL."""
    cleaned = clone_url.strip()
    if cleaned.startswith("https://"):
        return f"https://x-access-token:{token}@{cleaned[8:]}"
    return cleaned


def redact_token_from_url(url: str) -> str:
    """Sanitizes credentials embedded in URLs to prevent secret leakage in logs."""
    return _CREDENTIALS_RE.sub("https://[REDACTED_TOKEN]@", url)


def get_github_app_status() -> Dict[str, Any]:
    """Returns the current deployment status and installation URL for GitHub App."""
    configured = bool(
        settings.GITHUB_APP_ID
        and settings.GITHUB_APP_PRIVATE_KEY
        and settings.GITHUB_APP_SLUG
    )
    install_url = (
        f"https://github.com/apps/{settings.GITHUB_APP_SLUG}/installations/new"
        if configured
        else None
    )
    return {
        "configured": configured,
        "app_id": settings.GITHUB_APP_ID or None,
        "app_slug": settings.GITHUB_APP_SLUG or None,
        "install_url": install_url,
    }


async def resolve_project_clone_url(project: Any) -> str:
    """Returns authenticated clone URL if project has installation_id, otherwise raw url."""
    installation_id = getattr(project, "installation_id", None)
    raw_url = getattr(project, "github_url", "")
    if not installation_id:
        return raw_url
    try:
        token = await get_installation_access_token(int(installation_id))
        return build_authenticated_clone_url(raw_url, token)
    except Exception as exc:
        logger.warning(
            "failed_to_resolve_installation_token",
            project_id=str(getattr(project, "id", "")),
            error=str(exc),
        )
        return raw_url
