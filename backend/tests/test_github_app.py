"""Tests for GitHub App integration, webhook signature validation, and private repo ingestion."""

import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.services.github_app import (
    build_authenticated_clone_url,
    generate_app_jwt,
    get_github_app_status,
    get_installation_access_token,
    list_installation_repositories,
    redact_token_from_url,
    resolve_project_clone_url,
    verify_webhook_signature,
)


@pytest.fixture(scope="module")
def rsa_test_key():
    """Generates an in-memory RSA 2048-bit key for hermetic JWT signing tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return {"private": private_pem, "public": public_pem}


def test_webhook_signature_verification():
    """Verifies HMAC SHA-256 signature verification behavior."""
    secret = "test-webhook-secret-12345"
    payload = b'{"action": "created", "installation": {"id": 999}}'
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    valid_header = f"sha256={sig}"

    assert verify_webhook_signature(payload, valid_header, secret=secret) is True
    assert verify_webhook_signature(payload, "sha256=invalidhex", secret=secret) is False
    assert verify_webhook_signature(payload, None, secret=secret) is False
    assert verify_webhook_signature(payload, "sha1=deprecated", secret=secret) is False
    assert verify_webhook_signature(payload, valid_header, secret="") is False


def test_generate_app_jwt(rsa_test_key, monkeypatch):
    """Tests RS256 JWT generation, claims, and error when config missing."""
    token = generate_app_jwt(app_id="123456", private_key=rsa_test_key["private"])
    decoded = jwt.decode(token, rsa_test_key["public"], algorithms=["RS256"])
    assert decoded["iss"] == "123456" and decoded["exp"] > decoded["iat"]

    monkeypatch.setattr(settings, "GITHUB_APP_ID", "")
    monkeypatch.setattr(settings, "GITHUB_APP_PRIVATE_KEY", "")
    with pytest.raises(ValueError, match="configured"):
        generate_app_jwt(app_id="", private_key="")


@pytest.mark.anyio
async def test_get_installation_access_token(rsa_test_key):
    """Tests installation token exchange with mock HTTP response."""
    mock_response = httpx.Response(
        status_code=201,
        json={"token": "ghs_mock_installation_token_abc"},
        request=httpx.Request("POST", "https://api.github.com"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    token = await get_installation_access_token(
        installation_id=4567,
        app_jwt="fake-jwt-token",
        client=mock_client,
    )
    assert token == "ghs_mock_installation_token_abc"

    mock_fail = httpx.Response(status_code=403, text="Bad creds", request=mock_response.request)
    mock_client.post.return_value = mock_fail
    with pytest.raises(RuntimeError, match="status 403"):
        await get_installation_access_token(
            installation_id=4567, app_jwt="fake", client=mock_client
        )


@pytest.mark.anyio
async def test_list_installation_repositories():
    """Tests listing repositories accessible under an installation with pagination."""
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "total_count": 2,
            "repositories": [
                {"id": 1, "name": "priv", "full_name": "org/priv", "private": True,
                 "default_branch": "main", "clone_url": "https://github.com/org/priv.git",
                 "html_url": "https://github.com/org/priv"},
                {"id": 2, "name": "doc", "full_name": "org/doc", "private": False,
                 "default_branch": "main", "clone_url": "https://github.com/org/doc.git",
                 "html_url": "https://github.com/org/doc"},
            ],
        },
        request=httpx.Request("GET", "https://api.github.com"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_resp

    with patch(
        "app.services.github_app.get_installation_access_token",
        new_callable=AsyncMock,
        return_value="ghs_tok",
    ):
        total, repos = await list_installation_repositories(12345, client=mock_client)
        assert total == 2 and len(repos) == 2 and repos[0]["name"] == "priv"


def test_url_helpers_and_token_redaction():
    """Tests construction of authenticated clone URLs and credential redaction."""
    clone_url = "https://github.com/owner/secret-repo.git"
    token = "ghs_supersecret12345"
    auth_url = build_authenticated_clone_url(clone_url, token)
    assert "x-access-token:ghs_supersecret12345" in auth_url
    redacted = redact_token_from_url(auth_url)
    assert "ghs_supersecret12345" not in redacted
    assert "https://[REDACTED_TOKEN]@github.com/owner/secret-repo.git" == redacted


@pytest.mark.anyio
async def test_resolve_project_clone_url():
    """Tests project clone URL resolution based on installation_id presence."""
    pub_proj = Project(
        id=uuid.uuid4(), user_id=uuid.uuid4(), name="pub",
        github_url="https://github.com/test/pub", installation_id=None,
    )
    assert await resolve_project_clone_url(pub_proj) == "https://github.com/test/pub"

    priv_proj = Project(
        id=uuid.uuid4(), user_id=uuid.uuid4(), name="priv",
        github_url="https://github.com/test/priv", installation_id=8888,
    )
    with patch(
        "app.services.github_app.get_installation_access_token",
        new_callable=AsyncMock,
        return_value="ghs_tok",
    ):
        priv_url = await resolve_project_clone_url(priv_proj)
        assert "x-access-token:ghs_tok@github.com" in priv_url


def test_get_github_app_status():
    """Tests deployment status reporter."""
    status = get_github_app_status()
    assert "configured" in status and "app_id" in status and "install_url" in status


@pytest.mark.anyio
async def test_api_status_and_webhook():
    """Tests status and webhook receiver endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/github-app/status")
        assert resp.status_code == 200 and "configured" in resp.json()

        hook_fail = await ac.post("/api/v1/github-app/webhook", content=b"{}")
        assert hook_fail.status_code == 401

        secret = "secret-val"
        payload = b'{"action": "created"}'
        sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        with patch.object(settings, "GITHUB_APP_WEBHOOK_SECRET", secret):
            valid_resp = await ac.post(
                "/api/v1/github-app/webhook",
                content=payload,
                headers={"X-Hub-Signature-256": f"sha256={sig}", "X-GitHub-Event": "installation"},
            )
            assert valid_resp.status_code == 200 and valid_resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_api_private_repo_endpoints():
    """Tests authenticated repo listing, project creation, IDOR rejection, and 503 handling."""
    mock_user = User(id=uuid.uuid4(), email="dev@example.com")
    saved_overrides = dict(app.dependency_overrides)
    try:
        app.dependency_overrides[get_current_user] = lambda: mock_user
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.delete = AsyncMock()
        mock_db.add = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            mock_account = {"login": "dev", "type": "User"}
            repo_list = [
                {"id": 101, "name": "priv", "full_name": "corp/priv", "private": True,
                 "default_branch": "main", "clone_url": "https://github.com/corp/priv.git",
                 "html_url": "https://github.com/corp/priv"}
            ]
            patch_acct = patch(
                "app.api.v1.github_app.get_installation_account",
                new_callable=AsyncMock,
                return_value=mock_account,
            )
            patch_repos = patch(
                "app.api.v1.github_app.list_installation_repositories",
                new_callable=AsyncMock,
                return_value=(1, repo_list),
            )
            with patch_acct, patch_repos:
                # 1. Successful repository listing
                list_resp = await ac.get("/api/v1/github-app/installations/123/repositories")
                assert list_resp.status_code == 200 and list_resp.json()["total_count"] == 1

                # 2. Successful project creation
                with patch(
                    "app.api.v1.github_app.enqueue_clone_job",
                    new_callable=AsyncMock,
                    return_value="job-1",
                ):
                    create_resp = await ac.post(
                        "/api/v1/github-app/projects",
                        json={"full_name": "corp/priv", "installation_id": 123},
                    )
                    assert create_resp.status_code == 201
                    assert create_resp.json()["name"] == "priv"

                # 3. 503 Service Unavailable when background queue offline
                with patch(
                    "app.api.v1.github_app.enqueue_clone_job",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    fail_resp = await ac.post(
                        "/api/v1/github-app/projects",
                        json={"full_name": "corp/priv", "installation_id": 123},
                    )
                    assert fail_resp.status_code == 503
                    assert mock_db.delete.called

            # 4. IDOR rejection when unauthorized user attempts access
            patch_stranger = patch(
                "app.api.v1.github_app.get_installation_account",
                new_callable=AsyncMock,
                return_value={"login": "stranger", "type": "User"},
            )
            with patch_stranger:
                unauth_resp = await ac.get("/api/v1/github-app/installations/999/repositories")
                assert unauth_resp.status_code == 403
    finally:
        app.dependency_overrides = saved_overrides
