"""Hermetic unit and integration tests for Enhanced Defense Report aggregation and REST API."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import defense_store
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.schemas.architecture import (
    ArchitecturePatternType,
    ArchitectureReportResponse,
    DetectedPattern,
    PatternConfidenceTier,
)
from app.schemas.defense import (
    DefenseQuestionProgress,
    DefenseSessionState,
    DefenseStage,
)
from app.schemas.diagram import DiagramResponse, DiagramType
from app.schemas.question import GroundedQuestion, QuestionCategory
from app.schemas.report import (
    CategoryScore,
    DefenseReportResponse,
    EnhancedDefenseReportResponse,
)
from app.schemas.tech_audit import TechAuditReportResponse
from app.services.enhanced_report import generate_enhanced_defense_report
from tests.test_auth import create_test_jwt


def _create_sample_completed_session(
    project_id: uuid.UUID,
    score: float = 8.5,
) -> DefenseSessionState:
    """Helper creating a completed defense session."""
    q = GroundedQuestion(
        id="q1",
        category=QuestionCategory.ARCHITECTURE,
        question_text="Defend your modular monolith.",
        context_hint="app/main.py",
        cited_evidence_ids=["ev1"],
        cited_files=["backend/app/main.py"],
    )
    prog = DefenseQuestionProgress(
        question=q,
        status=DefenseStage.QUESTION_COMPLETED,
        final_score=9.0,
    )
    session = DefenseSessionState(
        session_id=str(uuid.uuid4()),
        project_id=str(project_id),
        status=DefenseStage.SESSION_COMPLETED,
        total_questions=1,
        current_question_index=0,
        overall_score=score,
    )
    session.questions = [prog]
    return session


def test_enhanced_defense_report_schema():
    """Verify EnhancedDefenseReportResponse instantiation and inheritance."""
    p_id = uuid.uuid4()
    s_id = uuid.uuid4()
    rep = EnhancedDefenseReportResponse(
        session_id=s_id,
        project_id=p_id,
        overall_score=9.0,
        verdict="Certified Principal Defense",
        summary="Outstanding defense.",
        category_scores=[
            CategoryScore(
                category=QuestionCategory.ARCHITECTURE,
                score=9.0,
                questions_count=1,
                status="passed",
                summary="Solid.",
            )
        ],
        key_strengths=["Architecture clarity"],
        critical_blind_spots=[],
        actionable_recommendations=[],
        total_questions=1,
        completed_at="2026-11-07T22:00:00Z",
        architecture_primary_pattern="Modular Monolith",
        architecture_confidence_tier="high",
        diagram_mermaid_code="flowchart TD\n  a --> b",
        tech_health_score=95,
        tech_flagged_count=0,
        tech_total_dependencies=12,
    )
    assert rep.architecture_primary_pattern == "Modular Monolith"
    assert rep.architecture_confidence_tier == "high"
    assert rep.tech_health_score == 95
    assert rep.tech_total_dependencies == 12


@pytest.mark.anyio
async def test_generate_enhanced_defense_report_service():
    """Verify service aggregates base report with architecture, diagram, and tech audit."""
    p_id = uuid.uuid4()
    session = _create_sample_completed_session(project_id=p_id)

    mock_project = Project(
        id=p_id,
        user_id=uuid.uuid4(),
        name="RepoDefense",
        github_url="https://github.com/test/repo",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = mock_res

    mock_base_report = DefenseReportResponse(
        session_id=uuid.UUID(session.session_id),
        project_id=p_id,
        overall_score=8.5,
        verdict="Certified Principal Defense",
        summary="Thorough understanding.",
        category_scores=[],
        key_strengths=["Clean separation"],
        critical_blind_spots=[],
        actionable_recommendations=[],
        total_questions=1,
        completed_at="2026-11-07T22:00:00Z",
    )

    mock_arch = ArchitectureReportResponse(
        project_id=str(p_id),
        project_name="RepoDefense",
        primary_pattern=DetectedPattern(
            pattern_type=ArchitecturePatternType.MODULAR_MONOLITH,
            pattern_name="Modular Monolith",
            confidence_score=0.92,
            tier=PatternConfidenceTier.HIGH,
            summary="Clear module boundaries.",
            indicators=[],
        ),
        secondary_patterns=[],
        architectural_risks=[],
        indicators=[],
        summary="Modular monolith structure.",
    )

    mock_diagram = DiagramResponse(
        project_id=str(p_id),
        project_name="RepoDefense",
        diagram_type=DiagramType.FLOWCHART_TD,
        mermaid_code="flowchart TD\n  Web --> API\n",
        nodes=[],
        edges=[],
        is_fallback=False,
        summary="System flow",
    )

    mock_tech = TechAuditReportResponse(
        project_id=str(p_id),
        project_name="RepoDefense",
        total_dependencies_audited=15,
        flagged_dependencies_count=1,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
        tech_health_score=85,
        audited_items=[],
    )

    with patch(
        "app.services.enhanced_report.generate_defense_report",
        return_value=mock_base_report,
    ), patch(
        "app.services.enhanced_report.detect_repository_architecture",
        return_value=mock_arch,
    ), patch(
        "app.services.enhanced_report.generate_project_architecture_diagram",
        return_value=mock_diagram,
    ), patch(
        "app.services.enhanced_report.audit_project_technology",
        return_value=mock_tech,
    ):
        report = await generate_enhanced_defense_report(session, mock_db)
        assert report.overall_score == 8.5
        assert report.architecture_primary_pattern == "Modular Monolith"
        assert report.architecture_confidence_tier == "high"
        assert "flowchart TD" in report.diagram_mermaid_code
        assert report.tech_health_score == 85
        assert report.tech_total_dependencies == 15


@pytest.mark.anyio
async def test_enhanced_report_endpoint_success():
    """Verify GET /api/v1/defense/sessions/{session_id}/enhanced-report returns 200 OK."""
    u_id = uuid.uuid4()
    p_id = uuid.uuid4()
    mock_user = User(id=u_id, email="report@example.com")
    mock_project = Project(id=p_id, user_id=u_id, name="TestRepo", github_url="https://github.com/test/repo")

    session = _create_sample_completed_session(project_id=p_id)
    await defense_store.save(session)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(u_id, mock_user.email)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/defense/sessions/{session.session_id}/enhanced-report",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == session.session_id
            assert data["project_id"] == str(p_id)
            assert data["overall_score"] == 8.5
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_enhanced_report_endpoint_incomplete_rejected():
    """Verify 400 Bad Request when session is not completed."""
    u_id = uuid.uuid4()
    p_id = uuid.uuid4()
    mock_user = User(id=u_id, email="report@example.com")
    mock_project = Project(id=p_id, user_id=u_id, name="TestRepo", github_url="https://github.com/test/repo")

    session = DefenseSessionState(
        session_id=str(uuid.uuid4()),
        project_id=str(p_id),
        status=DefenseStage.QUESTION_ACTIVE,
        total_questions=1,
    )
    await defense_store.save(session)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = mock_res

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(u_id, mock_user.email)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/defense/sessions/{session.session_id}/enhanced-report",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()
