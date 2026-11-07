"""Hermetic unit and integration tests for repository architecture pattern detection."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.analyzers.architecture import (
    detect_architectural_risks,
    eval_clean_architecture,
    eval_event_driven,
    eval_layered_architecture,
    eval_modular_monolith,
    eval_mvc,
    normalize_directory_tokens,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.architecture import (
    ArchitecturePatternType,
    PatternConfidenceTier,
)
from app.services.architecture import detect_repository_architecture
from tests.test_auth import create_test_jwt


def test_directory_normalization():
    """Verify path normalization, directory counting, and root handling."""
    paths = [
        "frontend/src/App.tsx",
        "frontend/src/index.css",
        "backend/app/main.py",
        "backend/app/api/v1/users.py",
        "Dockerfile",
        "README.md",
    ]
    counts, top_dirs = normalize_directory_tokens(paths)
    assert "frontend" in top_dirs
    assert "backend" in top_dirs
    assert counts["frontend"] == 2
    assert counts["backend"] == 2
    assert counts["<root>"] == 2


def test_eval_modular_monolith():
    """Verify modular monolith detection for frontend + backend repos."""
    top_dirs = {"frontend", "backend"}
    counts = {"frontend": 10, "backend": 15}
    deps = {"fastapi", "next", "pydantic"}

    pattern = eval_modular_monolith(top_dirs, counts, deps)
    assert pattern.pattern_type == ArchitecturePatternType.MODULAR_MONOLITH
    assert pattern.confidence_score >= 0.80
    assert pattern.tier == PatternConfidenceTier.HIGH
    assert len(pattern.indicators) >= 2


def test_eval_mvc():
    """Verify MVC detection for Django or Express controllers/models/views."""
    counts = {"controllers": 5, "models": 6, "views": 4}
    deps = {"django"}

    pattern = eval_mvc(counts, deps)
    assert pattern.pattern_type == ArchitecturePatternType.MVC
    assert pattern.confidence_score >= 0.80
    assert pattern.tier == PatternConfidenceTier.HIGH


def test_eval_clean_architecture():
    """Verify Clean / Hexagonal Architecture detection for domain + ports."""
    counts = {"domain": 8, "ports": 4, "adapters": 6}
    pattern = eval_clean_architecture(counts)
    assert pattern.pattern_type == ArchitecturePatternType.CLEAN_ARCHITECTURE
    assert pattern.confidence_score >= 0.75
    assert pattern.tier == PatternConfidenceTier.HIGH


def test_eval_event_driven():
    """Verify Event-Driven / Worker Queue architecture detection."""
    counts = {"workers": 4, "queues": 2}
    deps = {"arq", "redis"}
    ev_types = {"queue"}

    pattern = eval_event_driven(counts, deps, ev_types)
    assert pattern.pattern_type == ArchitecturePatternType.EVENT_DRIVEN
    assert pattern.confidence_score >= 0.85
    assert pattern.tier == PatternConfidenceTier.HIGH


def test_eval_layered_architecture():
    """Verify Layered Architecture detection for api + services + repositories."""
    counts = {"api": 5, "services": 6, "repositories": 4}
    pattern = eval_layered_architecture(counts)
    assert pattern.pattern_type == ArchitecturePatternType.LAYERED_ARCHITECTURE
    assert pattern.confidence_score >= 0.70
    assert pattern.tier == PatternConfidenceTier.HIGH


def test_detect_architectural_risks():
    """Verify detection of flat roots and fat routers."""
    counts = {"<root>": 20, "api": 5}
    risks = detect_architectural_risks(counts, file_count=20, deps=set(), evidence_types=set())

    risk_ids = {r.risk_id for r in risks}
    assert "FLAT_ROOT_HIERARCHY" in risk_ids
    assert "FAT_ROUTER_MISSING_SERVICES" in risk_ids


def _build_mock_db(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    file_paths: list[str],
    deps: list[str],
    evidences: list[str],
) -> tuple[AsyncMock, Project, User]:
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    user = User(
        id=user_id,
        email="architect@example.com",
        created_at=now,
        updated_at=now,
    )
    project = Project(
        id=project_id,
        user_id=user_id,
        name="ArchTestRepo",
        github_url="https://github.com/test/arch",
        default_branch="main",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        project_id=project_id,
        commit_hash="c0ffee1",
        created_at=now,
    )

    def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "from projects" in stmt_str:
            res.scalar_one_or_none.return_value = project
        elif "from repository_snapshots" in stmt_str:
            res.scalar_one_or_none.return_value = snapshot
        elif "from analyzed_files" in stmt_str:
            res.all.return_value = [(p,) for p in file_paths]
        elif "from dependencies" in stmt_str:
            res.all.return_value = [(d,) for d in deps]
        elif "from evidence" in stmt_str:
            res.all.return_value = [(e,) for e in evidences]
        else:
            res.scalar_one_or_none.return_value = None
            res.all.return_value = []
        return res

    mock_db.execute.side_effect = mock_execute
    return mock_db, project, user


@pytest.mark.anyio
async def test_detect_repository_architecture_service():
    """Verify service aggregates snapshot files and classifies primary pattern."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, project, _ = _build_mock_db(
        project_id=p_id,
        user_id=u_id,
        file_paths=["frontend/src/App.tsx", "backend/app/main.py"],
        deps=["fastapi", "next"],
        evidences=["framework"],
    )

    report = await detect_repository_architecture(project, mock_db)
    assert report.project_id == str(p_id)
    assert report.primary_pattern.pattern_type == ArchitecturePatternType.MODULAR_MONOLITH
    assert report.total_files_analyzed == 2


@pytest.mark.anyio
async def test_architecture_endpoint_success():
    """Verify GET /api/v1/projects/{project_id}/architecture returns 200 OK."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, _, user = _build_mock_db(
        project_id=p_id,
        user_id=u_id,
        file_paths=["frontend/src/App.tsx", "backend/app/main.py"],
        deps=["fastapi", "next"],
        evidences=["framework"],
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        transport = ASGITransport(app=app)
        token = create_test_jwt(str(u_id), "architect@example.com")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/projects/{p_id}/architecture",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_id"] == str(p_id)
            assert data["primary_pattern"]["pattern_type"] == "modular_monolith"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_architecture_endpoint_forbidden():
    """Verify GET /api/v1/projects/{project_id}/architecture returns 403 on other user."""
    p_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    mock_db, _, _ = _build_mock_db(
        project_id=p_id,
        user_id=owner_id,
        file_paths=[],
        deps=[],
        evidences=[],
    )
    other_user = User(id=other_user_id, email="other@example.com")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: other_user

    try:
        transport = ASGITransport(app=app)
        token = create_test_jwt(str(other_user_id), "other@example.com")
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/projects/{p_id}/architecture",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
