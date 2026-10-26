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
) -> str:
    """Generate a valid test JWT signed with configured Supabase secret."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": now + expires_in_sec,
        "iat": now,
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="module", autouse=True)
async def cleanup_db_engine():
    """Ensure clean connection pool lifecycle across test modules."""
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_create_project_unauthenticated_rejected():
    """Verify that project endpoints reject unauthenticated requests with 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/projects",
            json={"github_url": "https://github.com/fastapi/fastapi"},
        )
        assert response.status_code == 401


@pytest.mark.anyio
async def test_create_project_invalid_url_rejected():
    """Verify that invalid or non-GitHub URLs are rejected with HTTP 422."""
    user_id = uuid.uuid4()
    test_email = f"user_{uuid.uuid4().hex[:8]}@test.dev"
    token = create_test_jwt(user_id, test_email)

    invalid_urls = [
        "https://gitlab.com/owner/repo",
        "https://bitbucket.org/owner/repo",
        "not-a-url",
        "https://github.com/missing-repo",
        "https://github.com/",
    ]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for url in invalid_urls:
            response = await ac.post(
                "/api/v1/projects",
                headers={"Authorization": f"Bearer {token}"},
                json={"github_url": url},
            )
            assert response.status_code == 422, f"Expected 422 for URL: {url}"

    # Cleanup user
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            await session.delete(user)
            await session.commit()


@pytest.mark.anyio
async def test_create_project_success_and_duplicate_conflict():
    """Verify project creation with name derivation, followed by 409 on duplicate."""
    user_id = uuid.uuid4()
    token = create_test_jwt(user_id, f"project_test_{uuid.uuid4().hex[:6]}@repodefense.dev")
    repo_url = f"https://github.com/test-owner/test-repo-{uuid.uuid4().hex[:6]}.git"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Create Project
        response = await ac.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"github_url": repo_url},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(user_id)
        assert data["name"].startswith("test-repo-")
        assert not data["github_url"].endswith(".git")
        assert data["status"] == "pending"

        # 2. Attempt duplicate creation with same URL -> 409 Conflict
        dup_response = await ac.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"github_url": repo_url},
        )
        assert dup_response.status_code == 409
        assert "already exists" in dup_response.json()["detail"]

    # Cleanup created project and auto-provisioned user
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            await session.delete(user)
            await session.commit()


@pytest.mark.anyio
async def test_project_tenancy_isolation_and_crud():
    """Verify that users can only view, retrieve, and delete their own projects."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    token_a = create_test_jwt(user_a_id, f"usera_{uuid.uuid4().hex[:6]}@repodefense.dev")
    token_b = create_test_jwt(user_b_id, f"userb_{uuid.uuid4().hex[:6]}@repodefense.dev")

    project_a_id = None
    project_b_id = None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. User A creates Project A
        res_a = await ac.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "github_url": f"https://github.com/owner-a/repo-a-{uuid.uuid4().hex[:6]}",
                "name": "Custom Name A",
            },
        )
        assert res_a.status_code == 201
        project_a_id = res_a.json()["id"]
        assert res_a.json()["name"] == "Custom Name A"

        # 2. User B creates Project B
        res_b = await ac.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"github_url": f"https://github.com/owner-b/repo-b-{uuid.uuid4().hex[:6]}"},
        )
        assert res_b.status_code == 201
        project_b_id = res_b.json()["id"]

        # 3. User A lists projects -> sees ONLY Project A
        list_a = await ac.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_a.status_code == 200
        ids_a = [p["id"] for p in list_a.json()]
        assert project_a_id in ids_a
        assert project_b_id not in ids_a

        # 4. User B attempts to access Project A by ID -> 404 Not Found
        cross_res = await ac.get(
            f"/api/v1/projects/{project_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert cross_res.status_code == 404

        # 5. User A retrieves Project A -> 200
        get_res = await ac.get(
            f"/api/v1/projects/{project_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["id"] == project_a_id

        # 6. User A deletes Project A -> 204
        del_res = await ac.delete(
            f"/api/v1/projects/{project_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert del_res.status_code == 204

        # 7. Subsequent GET returns 404
        get_deleted = await ac.get(
            f"/api/v1/projects/{project_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert get_deleted.status_code == 404

    # Cleanup both users (cascades any remaining data)
    async with AsyncSessionLocal() as session:
        for uid in [user_a_id, user_b_id]:
            user = await session.get(User, uid)
            if user:
                await session.delete(user)
        await session.commit()
