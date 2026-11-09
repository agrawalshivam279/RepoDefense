"""Unit and integration tests for defense session state machine, evaluator, and REST API."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.evaluator import evaluate_candidate_defense, evaluate_secondary_turn
from app.ai.fallbacks import (
    build_deterministic_fallback_evaluation,
    build_deterministic_fallback_secondary,
)
from app.ai.fsm import (
    DefenseSessionStore,
    create_defense_session,
    defense_store,
    submit_defense_turn,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user
from app.main import app
from app.models.project import Project, User
from app.schemas.defense import DefenseSessionState, DefenseStage, TurnRole
from app.schemas.question import GroundedQuestion, QuestionCategory
from tests.test_auth import create_test_jwt


@pytest.fixture(autouse=True)
def default_offline_evaluator(monkeypatch):
    """Ensure fast, hermetic tests by disabling remote LLM calls by default."""
    monkeypatch.setattr(settings, "FREELLMAPI_API_KEY", "")


def _sample_question(index: int = 1) -> GroundedQuestion:
    return GroundedQuestion(
        id=f"q-{index}",
        category=QuestionCategory.SCALABILITY,
        question_text=f"How does component {index} handle high concurrency?",
        context_hint=f"Context for component {index}",
        cited_evidence_ids=[f"ev-{index}"],
        cited_files=[f"app/core/comp_{index}.py"],
    )


def test_defense_schemas_and_serialization():
    """Verify DefenseSessionState and turn schemas serialize correctly."""
    session = DefenseSessionState(
        project_id="proj-123",
        status=DefenseStage.QUESTION_ACTIVE,
        total_questions=1,
    )
    dumped = session.model_dump()
    assert dumped["project_id"] == "proj-123"
    assert dumped["status"] == "question_active"
    assert dumped["current_question_index"] == 0


def test_deterministic_fallback_evaluators():
    """Verify fallback evaluator logic for weak and strong defenses."""
    q = _sample_question(1)
    weak_out = build_deterministic_fallback_evaluation(q, "I don't know, copied from tutorial")
    assert not weak_out.passed_initial_defense
    assert weak_out.depth_score <= 5
    assert weak_out.stress_test_prompt is None
    assert weak_out.mentor_hint is not None

    strong_ans = (
        "We implemented async pooling with size 20, using backoff "
        "and read replicas to isolate queries."
    )
    strong_out = build_deterministic_fallback_evaluation(q, strong_ans)
    assert strong_out.passed_initial_defense
    assert strong_out.depth_score >= 6
    assert strong_out.stress_test_prompt is not None

    sec_fail = build_deterministic_fallback_secondary("Context", "too short")
    assert not sec_fail.handled_successfully
    assert sec_fail.follow_up_score == 4

    sec_pass = build_deterministic_fallback_secondary(
        "Context",
        "We apply distributed Redis rate limiting alongside circuit breakers to shed load.",
    )
    assert sec_pass.handled_successfully
    assert sec_pass.follow_up_score >= 7


@pytest.mark.anyio
async def test_fsm_empty_questions_rejected():
    """Verify creating a session with zero questions raises ValueError."""
    store = DefenseSessionStore()
    with pytest.raises(ValueError, match="zero questions"):
        await create_defense_session("proj-1", [], store=store)


@pytest.mark.anyio
async def test_fsm_passed_defense_and_stress_test_full_lifecycle():
    """Verify full interview loop with stress-test branch to completion."""
    store = DefenseSessionStore()
    q1 = _sample_question(1)

    session = await create_defense_session("proj-1", [q1], store=store)
    assert session.status == DefenseStage.QUESTION_ACTIVE
    assert session.current_question_index == 0
    assert len(session.turns) == 1
    assert session.turns[0].role == TurnRole.INTERVIEWER

    ans_1 = (
        "We isolated this into an async pipeline with background queues "
        "and exponential backoff."
    )
    session = await submit_defense_turn(session.session_id, ans_1, store=store)
    assert session.status == DefenseStage.STRESS_TEST_ACTIVE
    assert session.questions[0].status == DefenseStage.STRESS_TEST_ACTIVE
    assert session.questions[0].stress_test_prompt is not None
    assert len(session.turns) == 3

    stress_ans = "We enable Redis caching and connection pool limits to shed excessive load."
    session = await submit_defense_turn(session.session_id, stress_ans, store=store)
    assert session.status == DefenseStage.SESSION_COMPLETED
    assert session.questions[0].status == DefenseStage.QUESTION_COMPLETED
    assert session.questions[0].final_score is not None
    assert session.overall_score is not None
    assert 1.0 <= session.overall_score <= 10.0
    assert session.turns[-1].role == TurnRole.SYSTEM

    with pytest.raises(ValueError, match="already completed"):
        await submit_defense_turn(session.session_id, "extra answer", store=store)


@pytest.mark.anyio
async def test_fsm_failed_defense_and_mentor_retest_flow():
    """Verify that a weak defense branches to MENTOR_ACTIVE and re-test."""
    store = DefenseSessionStore()
    q1 = _sample_question(1)

    session = await create_defense_session("proj-2", [q1], store=store)
    weak_ans = "idk, boilerplate code"

    session = await submit_defense_turn(session.session_id, weak_ans, store=store)
    assert session.status == DefenseStage.MENTOR_ACTIVE
    assert session.questions[0].status == DefenseStage.MENTOR_ACTIVE
    assert session.questions[0].mentor_hint is not None
    assert session.questions[0].retest_question is not None

    retest_ans = "To recover, I will add an explicit timeout and circuit breaker fallback."
    session = await submit_defense_turn(session.session_id, retest_ans, store=store)
    assert session.status == DefenseStage.SESSION_COMPLETED
    assert session.questions[0].status == DefenseStage.QUESTION_COMPLETED
    assert session.overall_score is not None


@pytest.mark.anyio
async def test_fsm_nonexistent_session_rejected():
    """Verify submitting an answer to an unknown session raises KeyError."""
    store = DefenseSessionStore()
    with pytest.raises(KeyError, match="not found"):
        await submit_defense_turn("nonexistent-id", "some answer", store=store)


@pytest.mark.anyio
async def test_defense_api_unauthenticated_rejected():
    """Verify all defense endpoints reject unauthenticated requests with 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res1 = await ac.post(f"/api/v1/projects/{uuid.uuid4()}/defense/start", json={})
        assert res1.status_code == 401

        res2 = await ac.post("/api/v1/defense/sessions/test-id/answer", json={"answer": "abc"})
        assert res2.status_code == 401

        res3 = await ac.get("/api/v1/defense/sessions/test-id")
        assert res3.status_code == 401


@pytest.mark.anyio
async def test_defense_api_session_lifecycle():
    """Verify full HTTP defense session interaction with authentication."""
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    email = f"defense_{uuid.uuid4().hex[:6]}@repodefense.dev"
    mock_user = User(id=user_id, email=email)
    mock_project = Project(
        id=project_id,
        user_id=user_id,
        name="test-repo",
        github_url="https://github.com/test/test-repo",
    )
    async with AsyncSessionLocal() as db_session:
        db_session.add(mock_user)
        db_session.add(mock_project)
        await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        token = create_test_jwt(user_id, email)
        headers = {"Authorization": f"Bearer {token}"}

        q1 = _sample_question(1)
        session = await create_defense_session(str(project_id), [q1], store=defense_store)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            get_res = await ac.get(
                f"/api/v1/defense/sessions/{session.session_id}",
                headers=headers,
            )
            assert get_res.status_code == 200
            assert get_res.json()["session_id"] == session.session_id

            bad_get = await ac.get(
                f"/api/v1/defense/sessions/{uuid.uuid4()}",
                headers=headers,
            )
            assert bad_get.status_code == 404

            invalid_ans = await ac.post(
                f"/api/v1/defense/sessions/{session.session_id}/answer",
                json={"answer": "hi"},
                headers=headers,
            )
            assert invalid_ans.status_code == 422

            valid_ans = await ac.post(
                f"/api/v1/defense/sessions/{session.session_id}/answer",
                json={
                    "answer": (
                        "We encapsulated connection management in an async connection pool "
                        "with health probes and max lifetime configurations."
                    )
                },
                headers=headers,
            )
            assert valid_ans.status_code == 200
            assert valid_ans.json()["status"] in ["stress_test_active", "mentor_active"]
    finally:
        app.dependency_overrides.clear()
        async with AsyncSessionLocal() as db_session:
            u = await db_session.get(User, user_id)
            if u:
                await db_session.delete(u)
                await db_session.commit()


@pytest.mark.anyio
async def test_evaluator_llm_calls_with_mocks():
    """Verify evaluate_candidate_defense and secondary turn parsing with mocked LiteLLM."""
    q = _sample_question(1)
    mock_resp = AsyncMock()
    mock_choice = AsyncMock()
    mock_choice.message.content = (
        '{"passed_initial_defense": true, "depth_score": 8, "grounding_verified": true, '
        '"feedback": "Great architectural defense.", '
        '"stress_test_prompt": "What happens if traffic doubles?"}'
    )
    mock_resp.choices = [mock_choice]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_resp

        eval_out = await evaluate_candidate_defense(
            q,
            "Good defense answer",
            api_key="mock-key",
            max_retries=0,
            timeout_seconds=5.0,
        )
        assert eval_out.passed_initial_defense
        assert eval_out.depth_score == 8
        assert eval_out.stress_test_prompt == "What happens if traffic doubles?"

    mock_sec_resp = AsyncMock()
    mock_sec_choice = AsyncMock()
    mock_sec_choice.message.content = (
        '{"handled_successfully": true, "follow_up_score": 9, '
        '"feedback": "Excellent mitigation strategy."}'
    )
    mock_sec_resp.choices = [mock_sec_choice]

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = mock_sec_resp

        sec_out = await evaluate_secondary_turn(
            "What happens if traffic doubles?",
            "We autoscale worker pods and add Redis caching.",
            api_key="mock-key",
            max_retries=0,
            timeout_seconds=5.0,
        )
        assert sec_out.handled_successfully
        assert sec_out.follow_up_score == 9
