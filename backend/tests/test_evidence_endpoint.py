"""Hermetic unit and integration tests for the project evidence API endpoint."""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.analysis import Evidence
from app.models.project import Project, User


def create_test_jwt(user_id: uuid.UUID, email: str, expires_in_sec: int = 3600) -> str:
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


@pytest.mark.anyio
async def test_list_evidence_unauthenticated_rejected():
    """Verify that evidence endpoint rejects unauthenticated requests with 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/projects/{uuid.uuid4()}/evidence")
        assert res.status_code == 401


@pytest.mark.anyio
async def test_list_evidence_project_not_found():
    """Verify that querying evidence for a non-existent project returns 404."""
    user_id = uuid.uuid4()
    mock_user = User(id=user_id, email="evidence_tester@repodefense.dev")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = project_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(
                f"/api/v1/projects/{uuid.uuid4()}/evidence",
                headers=headers,
            )
            assert res.status_code == 404
            assert res.json()["detail"] == "Project not found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_evidence_success():
    """Verify that valid project returns all anchored evidence items with schema validation."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_user = User(id=user_id, email="evidence_tester@repodefense.dev")
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="test-repo",
        github_url="https://github.com/test/repo",
    )

    ev1 = Evidence(
        id=uuid.uuid4(),
        project_id=project_id,
        evidence_type="framework",
        title="FastAPI Web Framework",
        description="Async REST API layer",
        file_path="backend/app/main.py",
        start_line=1,
        end_line=50,
    )
    ev2 = Evidence(
        id=uuid.uuid4(),
        project_id=project_id,
        evidence_type="database",
        title="PostgreSQL 17 Database Connection",
        description="Async SQLAlchemy database connection pool",
        file_path="backend/app/core/database.py",
        start_line=15,
        end_line=45,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_db = AsyncMock()
    # Mock project lookup and evidence query
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = mock_project

    evidence_result = MagicMock()
    evidence_result.scalars.return_value.all.return_value = [ev1, ev2]

    mock_db.execute.side_effect = [project_result, evidence_result]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(
                f"/api/v1/projects/{project_id}/evidence",
                headers=headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 2
            assert data[0]["title"] == "FastAPI Web Framework"
            assert data[0]["evidence_type"] == "framework"
            assert data[0]["file_path"] == "backend/app/main.py"
            assert data[1]["title"] == "PostgreSQL 17 Database Connection"
            assert data[1]["evidence_type"] == "database"
            assert data[1]["start_line"] == 15
            assert data[1]["end_line"] == 45
    finally:
        app.dependency_overrides.clear()
