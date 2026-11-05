"""Hermetic unit and integration tests for repository defense coverage tracking."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import DefenseSessionStore
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.analysis import AnalyzedFile, Evidence
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.coverage import (
    CoverageStatus,
    CoverageTier,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
    DifficultyLevel,
)
from app.schemas.question import GroundedQuestion, QuestionCategory
from app.services.coverage import (
    _classify_evidence_priority,
    _resolve_module_path,
    calculate_project_coverage,
)
from tests.test_auth import create_test_jwt


def test_coverage_helpers():
    """Verify module path resolver and evidence priority classifier."""
    assert _resolve_module_path("backend/app/services/tx.py") == "backend/app"
    assert _resolve_module_path("frontend/src/App.tsx") == "frontend/src"
    assert _resolve_module_path("Dockerfile") == "root"
    assert _resolve_module_path("main.py") == "root"

    assert _classify_evidence_priority("Database") == "critical"
    assert _classify_evidence_priority("Auth") == "critical"
    assert _classify_evidence_priority("API_Endpoint") == "high"
    assert _classify_evidence_priority("Other") == "medium"


def _create_mock_db_with_project(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    files: list[AnalyzedFile],
    evidence: list[Evidence],
) -> AsyncMock:
    """Builds a mock AsyncSession returning test project, snapshot, files, and evidence."""
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    test_project = Project(
        id=project_id,
        user_id=user_id,
        name="CoverageTestRepo",
        github_url="https://github.com/test/repo",
        default_branch="main",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    test_snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        project_id=project_id,
        commit_hash="abc1234",
        created_at=now,
    )

    async def mock_get(entity, entity_id):
        if entity is Project and entity_id == project_id:
            return test_project
        return None

    mock_db.get.side_effect = mock_get

    def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "from repository_snapshots" in stmt_str:
            res.scalars.return_value.first.return_value = test_snapshot
        elif "from analyzed_files" in stmt_str:
            res.scalars.return_value.all.return_value = files
        elif "from evidence" in stmt_str:
            res.scalars.return_value.all.return_value = evidence
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
        return res

    mock_db.execute.side_effect = mock_execute
    return mock_db


@pytest.mark.anyio
async def test_calculate_coverage_zero_sessions():
    """Verify coverage calculation for a repository with no defense sessions conducted."""
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    snap_id = uuid.uuid4()
    ev1_id = uuid.uuid4()
    ev2_id = uuid.uuid4()

    files = [
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=snap_id, path="backend/app/auth.py",
                     language="Python", total_lines=120),
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=snap_id, path="backend/app/db.py",
                     language="Python", total_lines=200),
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=snap_id, path="frontend/src/App.tsx",
                     language="TypeScript", total_lines=80),
    ]
    evidence = [
        Evidence(id=ev1_id, project_id=proj_id, evidence_type="auth",
                 title="JWT Auth", description="Guards endpoints",
                 file_path="backend/app/auth.py", start_line=10, end_line=30),
        Evidence(id=ev2_id, project_id=proj_id, evidence_type="database",
                 title="Async Engine", description="PostgreSQL 17 pool",
                 file_path="backend/app/db.py", start_line=1, end_line=50),
    ]

    mock_db = _create_mock_db_with_project(proj_id, user_id, files, evidence)
    store = DefenseSessionStore()

    resp = await calculate_project_coverage(proj_id, user_id, mock_db, store=store)

    assert resp.total_files == 3
    assert resp.tested_files_count == 0
    assert resp.untested_files_count == 3
    assert resp.file_coverage_percentage == 0.0
    assert resp.total_evidence_items == 2
    assert resp.tested_evidence_count == 0
    assert resp.overall_coverage_tier == CoverageTier.NEEDS_DEFENSE
    assert len(resp.modules) == 2
    assert all(m.status == CoverageStatus.UNTESTED for m in resp.modules)
    assert len(resp.blind_spots) == 2
    assert resp.blind_spots[0].priority == "critical"


@pytest.mark.anyio
async def test_calculate_coverage_with_active_defense_sessions():
    """Verify coverage metrics accurately reflect tested questions, scores, and blind spots."""
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    snap_id = uuid.uuid4()
    ev_auth_id = uuid.uuid4()
    ev_db_id = uuid.uuid4()

    files = [
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=snap_id, path="backend/app/auth.py",
                     language="Python", total_lines=100),
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=snap_id, path="backend/app/db.py",
                     language="Python", total_lines=150),
    ]
    evidence = [
        Evidence(id=ev_auth_id, project_id=proj_id, evidence_type="auth",
                 title="JWT Auth", description="Auth guard",
                 file_path="backend/app/auth.py", start_line=5, end_line=25),
        Evidence(id=ev_db_id, project_id=proj_id, evidence_type="database",
                 title="Postgres Engine", description="Database connection",
                 file_path="backend/app/db.py", start_line=1, end_line=40),
    ]
    mock_db = _create_mock_db_with_project(proj_id, user_id, files, evidence)

    store = DefenseSessionStore()
    q1 = GroundedQuestion(
        id="q-auth",
        category=QuestionCategory.SECURITY,
        question_text="How do you handle JWT revocation?",
        context_hint="Auth Context",
        cited_evidence_ids=[str(ev_auth_id)],
        cited_files=["backend/app/auth.py"],
    )
    prog1 = DefenseQuestionProgress(
        question=q1,
        status=DefenseStage.QUESTION_COMPLETED,
        difficulty=DifficultyLevel.ADVANCED,
        initial_defense="We use a Redis blocklist for expired JWT tokens.",
        defense_score=8,
        final_score=9,
    )
    session = DefenseSessionState(
        session_id=str(uuid.uuid4()),
        project_id=str(proj_id),
        status=DefenseStage.SESSION_COMPLETED,
        current_question_index=0,
        total_questions=1,
        questions=[prog1],
    )
    await store.save(session)

    resp = await calculate_project_coverage(proj_id, user_id, mock_db, store=store)

    assert resp.total_files == 2
    assert resp.tested_files_count == 1
    assert resp.file_coverage_percentage == 50.0
    assert resp.total_evidence_items == 2
    assert resp.tested_evidence_count == 1
    assert resp.evidence_coverage_percentage == 50.0
    assert resp.total_lines_covered == 100

    auth_file = next(f for f in resp.files if f.file_path == "backend/app/auth.py")
    assert auth_file.is_tested is True
    assert auth_file.test_count == 1
    assert auth_file.average_score == 9.0
    assert auth_file.highest_difficulty == "advanced"

    assert len(resp.blind_spots) == 1
    assert resp.blind_spots[0].file_path == "backend/app/db.py"
    assert resp.blind_spots[0].title == "Postgres Engine"


@pytest.mark.anyio
async def test_calculate_coverage_multi_tenant_authorization():
    """Verify unauthorized users receive HTTP 403 and missing projects receive HTTP 404."""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    mock_db = _create_mock_db_with_project(proj_id, user_id, [], [])
    store = DefenseSessionStore()

    with pytest.raises(HTTPException) as exc_403:
        await calculate_project_coverage(proj_id, other_user_id, mock_db, store=store)
    assert exc_403.value.status_code == 403

    nonexistent_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_404:
        await calculate_project_coverage(nonexistent_id, user_id, mock_db, store=store)
    assert exc_404.value.status_code == 404


@pytest.mark.anyio
async def test_coverage_api_endpoint_via_client():
    """Verify GET /api/v1/projects/{project_id}/coverage endpoint via FastAPI client."""
    user_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    mock_user = User(id=user_id, email="cov_client@repodefense.dev")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    files = [
        AnalyzedFile(id=uuid.uuid4(), snapshot_id=uuid.uuid4(), path="app/main.py",
                     language="Python", total_lines=50),
    ]
    mock_db = _create_mock_db_with_project(proj_id, user_id, files, [])
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # Unauthenticated request rejected with 401
        app.dependency_overrides.pop(get_current_user, None)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res_401 = await ac.get(f"/api/v1/projects/{proj_id}/coverage")
            assert res_401.status_code == 401

        # Authenticated request returns 200 and valid schema
        app.dependency_overrides[get_current_user] = lambda: mock_user
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res_200 = await ac.get(f"/api/v1/projects/{proj_id}/coverage", headers=headers)
            assert res_200.status_code == 200
            data = res_200.json()
            assert data["project_id"] == str(proj_id)
            assert data["total_files"] == 1
            assert data["file_coverage_percentage"] == 0.0
            assert "modules" in data
            assert "files" in data
    finally:
        app.dependency_overrides.clear()
