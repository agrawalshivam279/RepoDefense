import time
import uuid

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.main import app
from app.models.project import User


def create_test_jwt(
    user_id: uuid.UUID,
    email: str,
    expires_in_sec: int = 3600,
    secret: str = settings.SUPABASE_JWT_SECRET,
    aud: str = "authenticated",
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
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test modules."""
    yield
    await engine.dispose()


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
