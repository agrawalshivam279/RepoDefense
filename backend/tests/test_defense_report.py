"""Hermetic unit and integration tests for defense report synthesis and REST API."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.fsm import create_defense_session, defense_store
from app.ai.report_generator import (
    aggregate_category_scores,
    build_deterministic_fallback_report,
    generate_defense_report,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.schemas.defense import DefenseSessionState, DefenseStage
from app.schemas.question import GroundedQuestion, QuestionCategory
from app.schemas.report import CategoryScore, DefenseReportResponse
from tests.test_auth import create_test_jwt


def _create_sample_completed_session(
    score: float = 8.5,
) -> DefenseSessionState:
    """Helper to create a fully completed defense session state."""
    q1 = GroundedQuestion(
        id="q1",
        category=QuestionCategory.ARCHITECTURE,
        question_text="Why did you choose a modular monolith architecture?",
        context_hint="app/main.py",
        cited_evidence_ids=["ev1"],
        cited_files=["backend/app/main.py"],
    )
    q2 = GroundedQuestion(
        id="q2",
        category=QuestionCategory.SCALABILITY,
        question_text="How do you handle connection pool exhaustion?",
        context_hint="app/core/database.py",
        cited_evidence_ids=["ev2"],
        cited_files=["backend/app/core/database.py"],
    )
    session = DefenseSessionState(
        session_id=str(uuid.uuid4()),
        project_id=str(uuid.uuid4()),
        status=DefenseStage.SESSION_COMPLETED,
        total_questions=2,
        current_question_index=1,
        overall_score=score,
    )
    from app.schemas.defense import DefenseQuestionProgress

    p1 = DefenseQuestionProgress(question=q1, status=DefenseStage.QUESTION_COMPLETED, final_score=9)
    p2 = DefenseQuestionProgress(question=q2, status=DefenseStage.QUESTION_COMPLETED, final_score=8)
    session.questions = [p1, p2]
    return session


def test_report_schemas_and_serialization():
    """Verify CategoryScore and DefenseReportResponse Pydantic validation."""
    cat = CategoryScore(
        category=QuestionCategory.SCALABILITY,
        score=8.5,
        questions_count=2,
        status="passed",
        summary="Sound handling of concurrency.",
    )
    assert cat.score == 8.5
    assert cat.status == "passed"

    rep = DefenseReportResponse(
        session_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        overall_score=8.5,
        verdict="Certified Principal Defense",
        summary="Strong defense.",
        category_scores=[cat],
        key_strengths=["Thorough code understanding"],
        critical_blind_spots=["Failover under split-brain"],
        actionable_recommendations=["Add automated load testing"],
        total_questions=2,
        completed_at="2026-11-04T00:00:00Z",
    )
    assert rep.overall_score == 8.5
    assert len(rep.category_scores) == 1


def test_score_aggregation_logic():
    """Verify mathematical category score grouping and status derivation."""
    session = _create_sample_completed_session(score=8.5)
    category_scores = aggregate_category_scores(session)
    assert len(category_scores) == 2
    cats = {c.category: c for c in category_scores}
    assert cats[QuestionCategory.ARCHITECTURE].score == 9.0
    assert cats[QuestionCategory.ARCHITECTURE].status == "passed"
    assert cats[QuestionCategory.SCALABILITY].score == 8.0
    assert cats[QuestionCategory.SCALABILITY].status == "passed"


def test_deterministic_fallback_report_verdicts():
    """Verify deterministic fallback report generation across score tiers."""
    s_high = _create_sample_completed_session(score=8.5)
    rep_high = build_deterministic_fallback_report(s_high, aggregate_category_scores(s_high))
    assert rep_high.verdict == "Certified Principal Defense"
    assert len(rep_high.key_strengths) >= 2

    s_mid = _create_sample_completed_session(score=6.0)
    s_mid.questions[0].final_score = 6
    s_mid.questions[1].final_score = 6
    rep_mid = build_deterministic_fallback_report(s_mid, aggregate_category_scores(s_mid))
    assert rep_mid.verdict == "Solid Architectural Defense"

    s_low = _create_sample_completed_session(score=4.0)
    s_low.questions[0].final_score = 4
    s_low.questions[1].final_score = 4
    rep_low = build_deterministic_fallback_report(s_low, aggregate_category_scores(s_low))
    assert rep_low.verdict == "Architectural Remediation Required"


@pytest.mark.anyio
async def test_generate_defense_report_fallback_on_llm_error():
    """Verify fallback report is produced if LiteLLM encounters an error."""
    session = _create_sample_completed_session(score=8.0)
    with patch("app.ai.report_generator.litellm.acompletion", side_effect=RuntimeError("LLM Down")):
        report = await generate_defense_report(
            session=session,
            api_key="dummy_key",
        )
        assert report.overall_score == 8.0
        assert report.verdict == "Certified Principal Defense"


@pytest.mark.anyio
async def test_report_endpoint_unauthenticated_rejected():
    """Verify 401 when accessing report endpoint without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get(f"/api/v1/defense/sessions/{uuid.uuid4()}/report")
        assert res.status_code == 401


@pytest.mark.anyio
async def test_report_endpoint_session_not_found():
    """Verify 404 when report requested for non-existent session."""
    user_id = uuid.uuid4()
    mock_user = User(id=user_id, email="report_tester@repodefense.dev")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(
                f"/api/v1/defense/sessions/{uuid.uuid4()}/report",
                headers=headers,
            )
            assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_report_endpoint_incomplete_session_rejected():
    """Verify 400 when defense session is still in progress."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_user = User(id=user_id, email="report_tester@repodefense.dev")
    mock_project = Project(id=project_id, user_id=user_id, name="repo", github_url="https://github.com/test/repo")

    q = GroundedQuestion(
        category=QuestionCategory.ARCHITECTURE,
        question_text="Why monolithic?",
        context_hint="hint",
        cited_evidence_ids=[],
        cited_files=[],
    )
    active_session = await create_defense_session(project_id=str(project_id), questions=[q])

    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = AsyncMock()
    proj_res = MagicMock()
    proj_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = proj_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(
                f"/api/v1/defense/sessions/{active_session.session_id}/report",
                headers=headers,
            )
            assert res.status_code == 400
            assert "completed before report" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
@patch("app.ai.report_generator.settings.FREELLMAPI_API_KEY", "")
async def test_report_endpoint_success():
    """Verify successful report generation for completed defense session."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_user = User(id=user_id, email="report_tester@repodefense.dev")
    mock_project = Project(id=project_id, user_id=user_id, name="repo", github_url="https://github.com/test/repo")

    session = _create_sample_completed_session(score=8.5)
    session.project_id = str(project_id)
    await defense_store.save(session)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    mock_db = AsyncMock()
    proj_res = MagicMock()
    proj_res.scalar_one_or_none.return_value = mock_project
    mock_db.execute.return_value = proj_res
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        token = create_test_jwt(user_id, mock_user.email)
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.get(
                f"/api/v1/defense/sessions/{session.session_id}/report",
                headers=headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert data["session_id"] == session.session_id
            assert data["project_id"] == str(project_id)
            assert data["overall_score"] == 8.5
            assert data["verdict"] == "Certified Principal Defense"
            assert len(data["category_scores"]) == 2
            assert len(data["key_strengths"]) >= 1
    finally:
        app.dependency_overrides.clear()
