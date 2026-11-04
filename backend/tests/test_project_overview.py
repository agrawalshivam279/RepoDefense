"""Hermetic unit and integration tests for repository project overview endpoint."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.analysis import Dependency
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.project import ProjectOverviewResponse
from app.schemas.summary import ProjectSummary
from tests.test_auth import create_test_jwt


@pytest.mark.anyio
async def test_project_overview_unauthenticated_rejected():
    """Verify that project overview rejects unauthenticated requests with HTTP 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/projects/{uuid.uuid4()}/overview")
        assert res.status_code == 401


@pytest.mark.anyio
async def test_project_overview_not_found():
    """Verify that requesting an overview for a non-existent project returns HTTP 404."""
    user_id = uuid.uuid4()
    mock_user = User(id=user_id, email="overview_tester@repodefense.dev")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_db = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(f"/api/v1/projects/{uuid.uuid4()}/overview", headers=headers)
            assert res.status_code == 404
            assert "Project not found" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_project_overview_pending_project():
    """Verify project overview response when repository ingestion is still pending."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_user = User(id=user_id, email="overview_tester@repodefense.dev")
    now = datetime.now(timezone.utc)
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="test-repo",
        github_url="https://github.com/org/test-repo",
        default_branch="main",
        status="pending",
        created_at=now,
        updated_at=now,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock DB query results in execution order
    mock_db = AsyncMock()
    res_proj = MagicMock()
    res_proj.scalar_one_or_none.return_value = mock_project

    res_snap = MagicMock()
    res_snap.scalar_one_or_none.return_value = None

    res_deps = MagicMock()
    res_deps.scalars.return_value.all.return_value = []

    res_ev_count = MagicMock()
    res_ev_count.scalar.return_value = 0

    mock_db.execute.side_effect = [res_proj, res_snap, res_deps, res_ev_count]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(f"/api/v1/projects/{project_id}/overview", headers=headers)
            assert res.status_code == 200
            data = res.json()
            overview = ProjectOverviewResponse.model_validate(data)
            assert overview.project_id == project_id
            assert overview.name == "test-repo"
            assert overview.status == "pending"
            assert overview.commit_hash is None
            assert overview.summary is None
            assert overview.metrics.total_files == 0
            assert overview.metrics.total_lines == 0
            assert overview.metrics.languages == []
            assert overview.dependencies == []
            assert overview.metrics.evidence_count == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_project_overview_completed_project():
    """Verify project overview response when repository has been analyzed with snapshot."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_user = User(id=user_id, email="overview_tester@repodefense.dev")
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="repodefense-core",
        github_url="https://github.com/org/repodefense-core",
        default_branch="main",
        status="cloned",
        created_at=now,
        updated_at=now,
    )

    ai_summary = ProjectSummary(
        title="RepoDefense Core Platform",
        tagline="Automated code defense and stress testing engine",
        primary_language="Python",
        detected_frameworks=["FastAPI", "Next.js"],
        architectural_style="Modular Monolith",
        key_components=["AST Analyzers", "LiteLLM Router", "Defense FSM"],
        potential_defense_topics=["Connection pooling", "Tree-sitter line boundaries"],
        narrative="Structured modular monolith built with FastAPI and Next.js 15 App Router.",
    )

    mock_snapshot = RepositorySnapshot(
        id=snapshot_id,
        project_id=project_id,
        commit_hash="93680f90169f958eecfb31f42b5774be6e46103e",
        summary=ai_summary.model_dump_json(),
        created_at=now,
    )

    mock_deps = [
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="fastapi",
            version="0.115.0",
            source_file="requirements.txt",
            is_dev=False,
        ),
        Dependency(
            id=uuid.uuid4(),
            project_id=project_id,
            name="pytest",
            version="8.3.5",
            source_file="requirements.txt",
            is_dev=True,
        ),
    ]

    class MockFileRow:
        def __init__(self, language: str, file_count: int, total_lines: int):
            self.language = language
            self.file_count = file_count
            self.total_lines = total_lines

    file_rows = [
        MockFileRow("Python", 12, 1850),
        MockFileRow("TypeScript", 8, 920),
    ]

    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock DB queries in sequence
    mock_db = AsyncMock()
    res_proj = MagicMock()
    res_proj.scalar_one_or_none.return_value = mock_project

    res_snap = MagicMock()
    res_snap.scalar_one_or_none.return_value = mock_snapshot

    res_deps = MagicMock()
    res_deps.scalars.return_value.all.return_value = mock_deps

    res_ev_count = MagicMock()
    res_ev_count.scalar.return_value = 5

    res_files = MagicMock()
    res_files.all.return_value = file_rows

    mock_db.execute.side_effect = [res_proj, res_snap, res_deps, res_ev_count, res_files]
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(f"/api/v1/projects/{project_id}/overview", headers=headers)
            assert res.status_code == 200
            data = res.json()
            overview = ProjectOverviewResponse.model_validate(data)

            assert overview.project_id == project_id
            assert overview.commit_hash == "93680f90169f958eecfb31f42b5774be6e46103e"
            assert overview.status == "cloned"

            # Check parsed AI summary
            assert overview.summary is not None
            assert overview.summary.title == "RepoDefense Core Platform"
            assert overview.summary.primary_language == "Python"
            assert overview.summary.architectural_style == "Modular Monolith"
            assert "FastAPI" in overview.summary.detected_frameworks

            # Check aggregated metrics
            assert overview.metrics.total_files == 20
            assert overview.metrics.total_lines == 2770
            assert len(overview.metrics.languages) == 2
            assert overview.metrics.languages[0].language == "Python"
            assert overview.metrics.languages[0].file_count == 12
            assert overview.metrics.evidence_count == 5

            # Check dependencies
            assert len(overview.dependencies) == 2
            assert overview.dependencies[0].name == "fastapi"
            assert not overview.dependencies[0].is_dev
            assert overview.dependencies[1].name == "pytest"
            assert overview.dependencies[1].is_dev
    finally:
        app.dependency_overrides.clear()
