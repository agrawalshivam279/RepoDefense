import time
import uuid
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import (
    decode_access_token,
    decode_access_token_async,
    verify_project_ownership,
)
from app.main import app
from app.models.project import User


def create_test_jwt(
    user_id: uuid.UUID,
    email: str,
    expires_in_sec: int = 3600,
    secret: str = settings.SUPABASE_JWT_SECRET,
    aud: str = "authenticated",
    app_metadata: dict | None = None,
    user_metadata: dict | None = None,
) -> str:
    """Generate a test JWT token signed with the configured secret and Supabase claims."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": aud,
        "role": "authenticated",
        "exp": now + expires_in_sec,
        "iat": now,
    }
    if app_metadata is not None:
        payload["app_metadata"] = app_metadata
    if user_metadata is not None:
        payload["user_metadata"] = user_metadata
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(scope="module", autouse=True)
def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test runs."""
    yield
    engine.sync_engine.dispose()


@pytest.mark.anyio
async def test_auth_me_unauthenticated_rejected():
    """Verify that requests without Authorization header return HTTP 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers


@pytest.mark.anyio
async def test_auth_me_invalid_token_rejected():
    """Verify that malformed or incorrectly signed tokens return HTTP 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Malformed token string
        response = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

        # 2. Token signed with wrong secret
        test_uid = uuid.uuid4()
        tampered_token = create_test_jwt(
            test_uid,
            "user@test.dev",
            secret="tampered-secret-key-min-32-chars-long",
        )
        response = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_auth_me_expired_token_rejected():
    """Verify that expired tokens return HTTP 401 with specific expiration detail."""
    test_uid = uuid.uuid4()
    expired_token = create_test_jwt(test_uid, "expired@test.dev", expires_in_sec=-60)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"


@pytest.mark.anyio
async def test_auth_me_valid_token_provisions_and_retrieves_user():
    """Verify that a valid token provisions the user record and returns the profile."""
    user_id = uuid.uuid4()
    email = f"auth_test_{uuid.uuid4().hex[:6]}@repodefense.dev"
    token = create_test_jwt(user_id, email)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user_id)
        assert data["email"] == email
        assert "created_at" in data
        assert "updated_at" in data

    # Verify user was synchronized into local PostgreSQL
    async with AsyncSessionLocal() as session:
        user_in_db = await session.get(User, user_id)
        assert user_in_db is not None
        assert user_in_db.email == email

        # Clean up test user
        await session.delete(user_in_db)
        await session.commit()


@pytest.mark.anyio
async def test_auth_me_existing_user():
    """Verify that subsequent requests for existing user resolve correctly."""
    user_id = uuid.uuid4()
    email = f"existing_test_{uuid.uuid4().hex[:6]}@repodefense.dev"

    # Pre-create user in DB
    async with AsyncSessionLocal() as session:
        user = User(id=user_id, email=email)
        session.add(user)
        await session.commit()

    token = create_test_jwt(user_id, email)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(user_id)
        assert response.json()["email"] == email

    # Clean up test user
    async with AsyncSessionLocal() as session:
        user_in_db = await session.get(User, user_id)
        if user_in_db:
            await session.delete(user_in_db)
            await session.commit()


@pytest.mark.anyio
async def test_auth_server_verified_github_binding_and_spoof_prevention():
    """Verifies that github_username is bound from app_metadata and rebinding is rejected."""
    user_id = uuid.uuid4()
    email = f"binding_{uuid.uuid4().hex[:6]}@repodefense.dev"

    # 1. User metadata alone must NOT bind github_username
    spoof_token = create_test_jwt(
        user_id, email, user_metadata={"user_name": "spoofed_login"}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {spoof_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["github_username"] is None

    # 2. Server-verified app_metadata properly binds github_username
    verified_token = create_test_jwt(
        user_id, email, app_metadata={"github_username": "verified-dev"}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {verified_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["github_username"] == "verified-dev"

    # 3. Attempt to rebind already bound handle with different token value is rejected
    rebind_token = create_test_jwt(
        user_id, email, app_metadata={"github_username": "malicious-takeover"}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        rebind_resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {rebind_token}"},
        )
        assert rebind_resp.status_code == 200
        assert rebind_resp.json()["github_username"] == "verified-dev"

    # Verify persisted User.github_username remains unchanged in PostgreSQL
    async with AsyncSessionLocal() as session:
        user_in_db = await session.get(User, user_id)
        assert user_in_db is not None
        assert user_in_db.github_username == "verified-dev"

    # 4. Malformed non-string claim in app_metadata is rejected with HTTP 401
    bad_token = create_test_jwt(
        user_id, email, app_metadata={"github_username": ["invalid_list"]}
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        bad_resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert bad_resp.status_code == 401
        assert "Malformed" in bad_resp.json()["detail"]

    # Clean up test user
    async with AsyncSessionLocal() as session:
        user_in_db = await session.get(User, user_id)
        if user_in_db:
            await session.delete(user_in_db)
            await session.commit()


def test_es256_jwks_token_verification_and_rejection():
    """Verifies ES256 Supabase JWKS validation and rejection of tampered/none alg tokens."""
    from fastapi import HTTPException

    private_key = ec.generate_private_key(ec.SECP256R1())
    other_private_key = ec.generate_private_key(ec.SECP256R1())
    user_id = uuid.uuid4()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": "es256@repodefense.dev",
        "aud": "authenticated",
        "role": "authenticated",
        "exp": now + 3600,
        "iat": now,
    }
    valid_es256 = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "kid-1"})
    wrong_es256 = jwt.encode(
        payload, other_private_key, algorithm="ES256", headers={"kid": "kid-1"}
    )
    none_alg = jwt.encode(payload, "", algorithm="none")

    mock_jwk_client = MagicMock()
    mock_jwk_client.get_signing_key_from_jwt.return_value = MagicMock(
        key=private_key.public_key()
    )

    with (
        patch("app.core.security.settings.SUPABASE_URL", "https://example.supabase.co"),
        patch("app.core.security._get_jwk_client", return_value=mock_jwk_client),
    ):
        decoded = decode_access_token(valid_es256)
        assert decoded.sub == user_id
        assert decoded.email == "es256@repodefense.dev"

        with pytest.raises(HTTPException) as bad_sig:
            decode_access_token(wrong_es256)
        assert bad_sig.value.status_code == 401

        with pytest.raises(HTTPException) as bad_alg:
            decode_access_token(none_alg)
        assert bad_alg.value.status_code == 401


def test_non_string_jwt_alg_rejected_with_401():
    """Rejects non-string alg headers (e.g. list) with 401 in sync and async decoders."""
    import asyncio
    import base64
    import json

    from fastapi import HTTPException

    def b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    token = f"{b64({'alg': [], 'typ': 'JWT'})}.{b64({'sub': str(uuid.uuid4())})}.sig"

    with pytest.raises(HTTPException) as sync_exc:
        decode_access_token(token)
    assert sync_exc.value.status_code == 401

    with pytest.raises(HTTPException) as async_exc:
        asyncio.run(decode_access_token_async(token))
    assert async_exc.value.status_code == 401


def test_verify_project_ownership_query_predicates():
    """Verifies verify_project_ownership filters by both Project.id and Project.user_id."""
    import asyncio
    from unittest.mock import AsyncMock

    proj_id, user_id = uuid.uuid4(), uuid.uuid4()
    mock_db = AsyncMock(
        execute=AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: MagicMock()))
    )
    asyncio.run(verify_project_ownership(str(proj_id), user_id, mock_db))
    stmt = mock_db.execute.call_args.args[0]
    compiled = stmt.compile()
    assert "projects.id" in compiled.string and "projects.user_id" in compiled.string
    assert {proj_id, user_id}.issubset(set(compiled.params.values()))
