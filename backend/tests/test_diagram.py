"""Hermetic unit and integration tests for Mermaid architecture diagram generation."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.analyzers.diagram import (
    build_deterministic_mermaid_diagram,
    classify_tier,
    sanitize_node_id,
    sanitize_node_label,
    validate_mermaid_syntax,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, RepositorySnapshot, User
from app.schemas.diagram import DiagramResponse, DiagramType
from app.services.diagram import generate_project_architecture_diagram
from tests.test_auth import create_test_jwt


def test_sanitize_node_id():
    """Verify conversion of package and directory names to valid Mermaid node IDs."""
    assert sanitize_node_id("FastAPI-Web") == "fastapi_web"
    assert sanitize_node_id("123_worker") == "n_123_worker"
    assert sanitize_node_id("@supabase/supabase-js") == "supabase_supabase_js"
    assert sanitize_node_id("   ") == "node"


def test_sanitize_node_label():
    """Verify quote replacement and length containment for Mermaid labels."""
    assert sanitize_node_label('FastAPI "REST" API') == "FastAPI &#x27;REST&#x27; API"
    expected_xss = "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert sanitize_node_label("<script>alert(1)</script>") == expected_xss
    long_label = "A" * 100
    assert len(sanitize_node_label(long_label)) <= 60


def test_classify_tier():
    """Verify architectural tier and node type mapping."""
    tier, n_type = classify_tier("Next.js 15")
    assert tier == "Client / Frontend Tier"
    assert n_type == "frontend"

    tier, n_type = classify_tier("FastAPI")
    assert tier == "API / Service Tier"
    assert n_type == "backend"

    tier, n_type = classify_tier("arq")
    assert tier == "Async Queues / Workers Tier"
    assert n_type == "queue"

    tier, n_type = classify_tier("pgvector")
    assert tier == "Persistence / Storage Tier"
    assert n_type == "database"

    tier, n_type = classify_tier("Supabase Auth")
    assert tier == "Auth & External Integrations Tier"
    assert n_type == "external"


def test_validate_mermaid_syntax():
    """Verify syntax checks for Mermaid flowchart declarations."""
    valid_code = (
        'flowchart TD\n'
        '  subgraph S1["Tier 1"]\n'
        '    n1["Node 1"]\n'
        '  end\n'
        '  n1 --> n2["Node 2"]\n'
    )
    assert validate_mermaid_syntax(valid_code) is True

    # Missing flowchart header
    assert validate_mermaid_syntax('graph TD\n  n1 --> n2') is False
    # Unbalanced subgraphs
    assert validate_mermaid_syntax('flowchart TD\n  subgraph S1["Tier 1"]\n    n1\n') is False
    # Odd quotes
    assert validate_mermaid_syntax('flowchart TD\n  n1["Unbalanced quote]\n') is False


def test_build_deterministic_mermaid_diagram():
    """Verify deterministic flowchart generation from project metadata."""
    code, nodes, edges, summary = build_deterministic_mermaid_diagram(
        project_name="RepoDefense",
        dependencies=["fastapi", "next", "sqlalchemy", "arq", "supabase"],
        evidence_tags=["JWT Auth (auth)", "PostgreSQL (database)"],
        top_directories=["frontend", "backend", "workers"],
    )

    assert code.startswith("flowchart TD")
    assert "subgraph" in code
    assert len(nodes) >= 5
    assert len(edges) >= 2
    assert "RepoDefense" in summary
    assert validate_mermaid_syntax(code) is True


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
        email="diagram@example.com",
        created_at=now,
        updated_at=now,
    )
    project = Project(
        id=project_id,
        user_id=user_id,
        name="DiagramRepo",
        github_url="https://github.com/test/diagram",
        default_branch="main",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        project_id=project_id,
        commit_hash="d1a97a",
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
            res.all.return_value = [(e, "framework") for e in evidences]
        else:
            res.scalar_one_or_none.return_value = None
            res.all.return_value = []
        return res

    mock_db.execute.side_effect = mock_execute
    return mock_db, project, user


@pytest.mark.anyio
async def test_diagram_service_fallback():
    """Verify diagram service produces deterministic fallback when LLM is unconfigured."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, project, _ = _build_mock_db(
        project_id=p_id,
        user_id=u_id,
        file_paths=["frontend/src/App.tsx", "backend/app/main.py"],
        deps=["fastapi", "next"],
        evidences=["FastAPI REST Router"],
    )

    diagram = await generate_project_architecture_diagram(
        project=project,
        db=mock_db,
        api_key="",
    )
    assert diagram.project_id == str(p_id)
    assert diagram.diagram_type == DiagramType.FLOWCHART_TD
    assert diagram.is_fallback is True
    assert "flowchart TD" in diagram.mermaid_code


@pytest.mark.anyio
async def test_diagram_endpoint_success():
    """Verify GET /api/v1/projects/{project_id}/diagram returns 200 OK."""
    p_id = uuid.uuid4()
    u_id = uuid.uuid4()
    mock_db, project, user = _build_mock_db(
        project_id=p_id,
        user_id=u_id,
        file_paths=["frontend/src/App.tsx", "backend/app/main.py"],
        deps=["fastapi", "next"],
        evidences=["FastAPI REST Router"],
    )

    mock_response = DiagramResponse(
        project_id=str(p_id),
        project_name="DiagramRepo",
        diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code="flowchart TD\n  a --> b\n",
        nodes=[],
        edges=[],
        is_fallback=True,
        summary="Test diagram summary",
    )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with patch(
            "app.api.v1.diagram.generate_project_architecture_diagram",
            return_value=mock_response,
        ):
            transport = ASGITransport(app=app)
            token = create_test_jwt(str(u_id), "diagram@example.com")
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    f"/api/v1/projects/{p_id}/diagram",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["project_id"] == str(p_id)
                assert "flowchart TD" in data["mermaid_code"]
                assert data["is_fallback"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_diagram_endpoint_forbidden():
    """Verify GET /api/v1/projects/{project_id}/diagram returns 403 on non-owner."""
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
                f"/api/v1/projects/{p_id}/diagram",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
